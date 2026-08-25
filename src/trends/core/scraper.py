import asyncio
import re
from playwright.async_api import async_playwright

# Limita quantos Chromiums este worker pode ter abertos ao mesmo tempo.
# Ver "Diagnóstico dos picos de CPU" seção I: Semaphore(2) é o equilíbrio
# recomendado para 2 vCPU / 4 GB RAM.
MAX_CONCURRENT_BROWSERS = 2
_browser_semaphore = asyncio.Semaphore(MAX_CONCURRENT_BROWSERS)


class TrendsFetchError(Exception):
    """Levantada quando não é possível obter as tendências do Google Trends."""


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
    async with _browser_semaphore:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                try:
                    context = await browser.new_context()
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
                    # Garante o fechamento do Chromium mesmo se um timeout ou outra
                    # exceção ocorrer entre o launch() e o fim do scraping.
                    await browser.close()

        except Exception as e:
            print("⚠️ Erro ao buscar dados:", e)
            raise TrendsFetchError(str(e)) from e
