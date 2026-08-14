import asyncio
from trends.core.scraper import fetch_trends, TrendsFetchError
from trends.core.cache import cache_set

async def update_trends():
    print("🔄 Atualizando cache de tendências...")
    try:
        data = await fetch_trends("BR", 0)
    except TrendsFetchError as e:
        print("⚠️ Atualização de cache pulada:", e)
        return
    await cache_set("trends:BR:0", data)

def update_trends_job():
    asyncio.run(update_trends())
