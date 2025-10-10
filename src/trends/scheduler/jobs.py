import asyncio
from trends.core.scraper import fetch_trends
from trends.core.cache import cache_set

async def update_trends():
    print("🔄 Atualizando cache de tendências...")
    data = await fetch_trends("BR", 0)
    await cache_set("trends:BR:0", data)

def update_trends_job():
    asyncio.run(update_trends())
