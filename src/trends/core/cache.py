import json
import os
import redis.asyncio as redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

# Conecta no Redis
redis_client = redis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)

STALE_PREFIX = "stale"
STALE_TTL_SECONDS = 24 * 60 * 60  # fallback usado quando a janela de baixo tráfego bloqueia um novo scrape


async def cache_get(key: str):
    value = await redis_client.get(key)
    return json.loads(value) if value else None


async def cache_get_stale(key: str):
    value = await redis_client.get(f"{STALE_PREFIX}:{key}")
    return json.loads(value) if value else None


async def cache_set(key: str, data, expire_seconds: int = 900):
    payload = json.dumps(data)
    await redis_client.set(key, payload, ex=expire_seconds)
    await redis_client.set(f"{STALE_PREFIX}:{key}", payload, ex=STALE_TTL_SECONDS)


async def acquire_lock(key: str, ttl_seconds: int) -> bool:
    """Tenta adquirir um lock distribuído no Redis (SET NX EX).

    Usado para eleição de líder entre múltiplos workers: independente de
    quantos processos rodem em produção, só o primeiro a chamar isto dentro
    da janela de ttl_seconds obtém True e deve executar a tarefa.
    """
    return bool(await redis_client.set(key, "1", nx=True, ex=ttl_seconds))
