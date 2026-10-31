import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, billing, catalog, health, profile, quotations, subscriptions, users
from app.core.config import settings
from app.services.billing_scheduler import billing_scheduler_loop


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler_task = None
    if settings.billing_scheduler_enabled:
        scheduler_task = asyncio.create_task(billing_scheduler_loop(), name="billing-scheduler")
    try:
        yield
    finally:
        if scheduler_task:
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="Brightloop subscription management API.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(catalog.router, prefix="/api")
app.include_router(quotations.router, prefix="/api")
app.include_router(subscriptions.router, prefix="/api")
app.include_router(billing.router, prefix="/api")


@app.get("/", include_in_schema=False)
def root():
    return {"service": "brightloop", "docs": "/docs", "health": "/api/health"}
