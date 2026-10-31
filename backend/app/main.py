from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, billing, catalog, health, profile, quotations, subscriptions, users
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="2.0.0", description="Brightloop subscription management API.")
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
