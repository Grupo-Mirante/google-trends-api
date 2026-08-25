import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from trends.app.routes import router as trends_router
from trends.scheduler.jobs import update_trends


@asynccontextmanager
async def lifespan(app: FastAPI):
    # AsyncIOScheduler roda o job como coroutine no mesmo event loop do
    # worker, em vez de asyncio.run() criar/fechar um loop novo a cada
    # disparo — isso é o que causava o RuntimeError: Event loop is closed
    # no cliente Redis assíncrono global.
    scheduler = AsyncIOScheduler()
    scheduler.add_job(update_trends, "interval", minutes=10)
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    app = FastAPI(title="Google Trends API", version="0.1.0", lifespan=lifespan)

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

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run("trends.main:app", host="0.0.0.0", port=port, reload=True)
