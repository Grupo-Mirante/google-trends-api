import json
import redis.asyncio as redis

# Conecta no Redis
redis_client = redis.from_url("redis://redis:6379", decode_responses=True)


async def cache_get(key: str):
    value = await redis_client.get(key)
    return json.loads(value) if value else None


async def cache_set(key: str, data, expire_seconds: int = 600):
    await redis_client.set(key, json.dumps(data), ex=expire_seconds)
