from fastapi import APIRouter, Query, HTTPException
from trends.core.scraper import fetch_trends, TrendsFetchError
from trends.core.cache import cache_get, cache_get_stale, cache_set
from trends.core.utils import em_horario_de_pausa

# router = APIRouter(prefix="/trends", tags=["trends"])
router = APIRouter(tags=["trends"])
@router.get("/trends")
async def get_trends(geo: str = Query("BR"), category: int = Query(0)):
    """Retorna as tendências do Google Trends."""
    cache_key = f"trends:{geo}:{category}"
    cached_data = await cache_get(cache_key)

    if cached_data:
        return {"cached": True, "trends": cached_data}

    if em_horario_de_pausa():
        stale_data = await cache_get_stale(cache_key)
        if stale_data:
            return {"cached": True, "stale": True, "trends": stale_data}
        raise HTTPException(
            status_code=503,
            detail="Atualização pausada no horário de baixo tráfego (00:00–06:00). Tente novamente mais tarde.",
        )

    try:
        data = await fetch_trends(geo, category)
    except TrendsFetchError:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível obter as tendências do Google Trends no momento.",
        )

    await cache_set(cache_key, data)
    return {"cached": False, "trends": data}
