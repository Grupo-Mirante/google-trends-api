import asyncio
from trends.core.scraper import fetch_trends, TrendsFetchError
from trends.core.cache import cache_set
from trends.core.utils import em_horario_de_pausa

async def update_trends():
    if em_horario_de_pausa():
        print("⏸️ Atualização pulada: horário de baixo tráfego (00:00–06:00).")
        return
    print("🔄 Atualizando cache de tendências...")
    try:
        data = await fetch_trends("BR", 0)
    except TrendsFetchError as e:
        print("⚠️ Atualização de cache pulada:", e)
        return
    await cache_set("trends:BR:0", data)

def update_trends_job():
    asyncio.run(update_trends())
