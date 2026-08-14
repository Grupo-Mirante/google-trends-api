from fastapi import APIRouter, Query, HTTPException
from trends.core.scraper import fetch_trends, TrendsFetchError
from trends.core.cache import cache_get, cache_set

# router = APIRouter(prefix="/trends", tags=["trends"])
router = APIRouter(tags=["trends"])
@router.get("/trends")
async def get_trends(geo: str = Query("BR"), category: int = Query(0)):
    """Retorna as tendências do Google Trends."""
    cache_key = f"trends:{geo}:{category}"
    cached_data = await cache_get(cache_key)

    if cached_data:
        return {"cached": True, "trends": cached_data}

    try:
        data = await fetch_trends(geo, category)
    except TrendsFetchError:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível obter as tendências do Google Trends no momento.",
        )

    await cache_set(cache_key, data)
    return {"cached": False, "trends": data}
