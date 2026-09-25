import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config.settings import settings
from app.database.connection import engine, Base, async_session_factory
from app.routers import auth, users, shelters, hospitals, disasters, alerts, routes, weather, location, ai, risk as risk_router, sos as sos_router, admin as admin_router
from app.services.disaster_sources.background_refresh import BackgroundIngestion

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_background_ingestion = BackgroundIngestion(async_session_factory)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _background_ingestion.start()

    yield

    await _background_ingestion.stop()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(shelters.router)
app.include_router(hospitals.router)
app.include_router(disasters.router)
app.include_router(alerts.router)
app.include_router(routes.router)
app.include_router(weather.router)
app.include_router(location.router)
app.include_router(ai.router)
app.include_router(risk_router.router)
app.include_router(sos_router.router)
app.include_router(admin_router.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}
