import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

QUIET_HOURS_TZ = os.getenv("QUIET_HOURS_TZ", "America/Sao_Paulo")
QUIET_HOURS_START = int(os.getenv("QUIET_HOURS_START", "0"))
QUIET_HOURS_END = int(os.getenv("QUIET_HOURS_END", "6"))


def em_horario_de_pausa(now: datetime | None = None) -> bool:
    """Indica se o horário atual está na janela de baixo tráfego em que o Chromium não deve ser iniciado."""
    hora_atual = (now or datetime.now(ZoneInfo(QUIET_HOURS_TZ))).hour
    return QUIET_HOURS_START <= hora_atual < QUIET_HOURS_END


def formatar_dados(item: dict) -> dict:
    """Recebe um item bruto e retorna dados formatados."""
    volume_match = re.search(r"(\d+(?:[.,]\d+)?\s*(?:mil|M|K|B)?\+?)", item.get("data_volume", ""), flags=re.IGNORECASE)
    volume = volume_match.group(1) if volume_match else None

    perc_match = re.search(r"(\d{1,3}(?:[.,]\d{3})*%|\d+%)", item.get("data_volume", ""))
    variation = perc_match.group(1) if perc_match else None

    time_match = re.search(r"(há\s+\d+\s+\w+)", item.get("duration", ""))
    duration = time_match.group(1) if time_match else None

    keywords_raw = item.get("keywords", [])
    keywords = []
    for kw in keywords_raw:
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
