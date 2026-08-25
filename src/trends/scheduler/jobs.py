from trends.core.scraper import fetch_trends, TrendsFetchError
from trends.core.cache import cache_set, acquire_lock
from trends.core.utils import em_horario_de_pausa

# Chave de lock compartilhada entre todos os workers: garante que só um deles
# execute o job em cada disparo do agendador, mesmo com múltiplos processos
# rodando em produção. TTL menor que o intervalo do job (10 min) evita que um
# lock travado por um worker que caiu bloqueie o próximo ciclo.
JOB_LOCK_KEY = "trends:job:lock"
JOB_LOCK_TTL_SECONDS = 9 * 60


async def update_trends():
    if em_horario_de_pausa():
        print("⏸️ Atualização pulada: horário de baixo tráfego (00:00–06:00).")
        return

    if not await acquire_lock(JOB_LOCK_KEY, JOB_LOCK_TTL_SECONDS):
        # Outro worker já adquiriu o lock deste ciclo e vai executar o job.
        return

    print("🔄 Atualizando cache de tendências...")
    try:
        data = await fetch_trends("BR", 0)
    except TrendsFetchError as e:
        print("⚠️ Atualização de cache pulada:", e)
        return
    await cache_set("trends:BR:0", data)
