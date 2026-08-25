import asyncio
import os
import re
import time
from playwright.async_api import async_playwright

# Limita quantas paginas este worker pode ter carregando ao mesmo tempo no
# browser compartilhado. Ver "Diagnóstico dos picos de CPU" seção I:
# Semaphore(2) é o equilíbrio recomendado para 2 vCPU / 4 GB RAM.
MAX_CONCURRENT_SCRAPES = 2
_scrape_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)

# Recicla o browser periodicamente para evitar acúmulo de memória em um
# processo Chromium de longa duração (páginas do Google Trends são pesadas
# em JS). Configurável via env porque o ponto ideal depende do tráfego real.
BROWSER_MAX_AGE_SECONDS = int(os.getenv("BROWSER_MAX_AGE_HOURS", "6")) * 3600
BROWSER_MAX_REQUESTS = int(os.getenv("BROWSER_MAX_REQUESTS", "300"))


class TrendsFetchError(Exception):
    """Levantada quando não é possível obter as tendências do Google Trends."""


class BrowserManager:
    """Mantém um único Chromium vivo por worker e reutilizado entre requisições.

    Cada chamada a fetch_trends() só abre/fecha um `context` + `page` (baratos)
    em cima desse browser persistente — o launch() caro do Chromium acontece
    uma vez, não a cada scrape. O browser é reciclado por idade/uso e
    relançado automaticamente se cair (crash, kill externo etc.).
    """

    def __init__(self, max_age_seconds: int = BROWSER_MAX_AGE_SECONDS, max_requests: int = BROWSER_MAX_REQUESTS):
        self.max_age_seconds = max_age_seconds
        self.max_requests = max_requests
        self._playwright = None
        self._browser = None
        self._launched_at = 0.0
        self._request_count = 0
        self._lock = asyncio.Lock()

    async def start(self):
        async with self._lock:
            if self._browser is None:
                await self._launch()

    async def shutdown(self):
        async with self._lock:
            await self._close()

    async def get_context(self):
        async with self._lock:
            if self._browser is None or not self._browser.is_connected():
                await self._close()
                await self._launch()
            elif self._should_recycle():
                await self._close()
                await self._launch()
            self._request_count += 1
            browser = self._browser
        return await browser.new_context()

    def _should_recycle(self) -> bool:
        age_expired = (time.monotonic() - self._launched_at) > self.max_age_seconds
        overused = self._request_count >= self.max_requests
        return age_expired or overused

    async def _launch(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._launched_at = time.monotonic()
        self._request_count = 0

    async def _close(self):
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        self._browser = None
        self._playwright = None


browser_manager = BrowserManager()


def formatar_dados(item: dict) -> dict:
    volume_match = re.search(r"(\d+(?:[.,]\d+)?\s*(?:mil|M|K|B)?\+?)", item.get("data_volume", ""), flags=re.IGNORECASE)
    volume = volume_match.group(1) if volume_match else None
    perc_match = re.search(r"(\d{1,3}(?:[.,]\d{3})*%|\d+%)", item.get("data_volume", ""))
    variation = perc_match.group(1) if perc_match else None
    time_match = re.search(r"(há\s+\d+\s+\w+)", item.get("duration", ""))
    duration = time_match.group(1) if time_match else None

    keywords = []
    for kw in item.get("keywords", []):
        parts = [p.strip() for p in kw.split("\n") if p.strip()]
        for p in parts:
            if "Search term" not in p and "Explore" not in p and "query_stats" not in p:
                if p not in keywords:
                    keywords.append(p)

    title = item.get("title", "").split("\n")[0].strip()
    return {
        "title": title,
        "search_volume": volume,
        "variation": variation,
        "duration": duration,
        "keywords": keywords
    }


async def fetch_trends(geo="BR", category=0):
    # O Google Trends ignora o parâmetro `category` na querystring: o filtro só é
    # aplicado quando o dropdown de categoria é acionado no client-side. Por isso,
    # com category != 0, precisamos abrir o dropdown e clicar na opção correspondente
    # em vez de confiar na URL.
    url = f"https://trends.google.com.br/trending?geo={geo}"
    data = []
    async with _scrape_semaphore:
        try:
            context = await browser_manager.get_context()
            try:
                page = await context.new_page()

                await page.goto(url, timeout=60000)
                await page.wait_for_selector("tr[data-row-id]")

                if category:
                    dropdown = await page.query_selector("text=Todas as categorias")
                    if dropdown:
                        await dropdown.click()
                        # :visible é necessário porque outros dropdowns da página (ex.: filtro
                        # de período) reutilizam os mesmos valores numéricos em data-value
                        # (ex.: "Últimas 4 horas" também tem data-value="4", colidindo com a
                        # categoria Entretenimento) enquanto estão ocultos no DOM.
                        option = await page.wait_for_selector(f'[data-value="{category}"]:visible', timeout=5000)
                        await option.click()
                        await page.wait_for_timeout(1000)
                        await page.wait_for_selector("tr[data-row-id]")

                rows = await page.query_selector_all("tr[data-row-id]")

                for row in rows:
                    cells = await row.query_selector_all("td")
                    if cells:
                        text_cells = [await cell.inner_text() for cell in cells]
                        item_data = {
                            "index": text_cells[0],
                            "title": text_cells[1],
                            "data_volume": text_cells[2],
                            "duration": text_cells[3],
                            "keywords": [text_cells[4]],
                        }
                        data.append(formatar_dados(item_data))

                return data
            finally:
                # Fecha só o context/page desta requisição — o browser
                # persistente permanece vivo para a próxima chamada.
                await context.close()

        except Exception as e:
            print("⚠️ Erro ao buscar dados:", e)
            raise TrendsFetchError(str(e)) from e
