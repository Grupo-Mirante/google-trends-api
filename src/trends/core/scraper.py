import re
from playwright.async_api import async_playwright


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
    url = f"https://trends.google.com.br/trending?geo={geo}&category={category}"
    data = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(url, timeout=60000)
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

            await browser.close()
            return data

    except Exception as e:
        print("⚠️ Erro ao buscar dados:", e)
        return [{"error": "erro ao buscar informações"}]
