import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from trends.app.routes import router as trends_router
from trends.scheduler.jobs import update_trends_job


def create_app() -> FastAPI:
    app = FastAPI(title="Google Trends API", version="0.1.0")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost",
            "http://127.0.0.1:5173",
            "https://radar-tendencias.onrender.com",
            "http://homolog-admin.imirante.com",
            "https://novoadmin.imirante.com",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rotas
    app.include_router(trends_router)

    # Scheduler (APScheduler)
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_trends_job, "interval", minutes=10)
    scheduler.start()

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run("trends.main:app", host="0.0.0.0", port=port, reload=True)
