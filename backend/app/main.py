from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, gardens, layouts, plants, plans, properties
from app.core import get_settings

settings = get_settings()

app = FastAPI(title="Jakerton's Garden Planning Tool", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(properties.router, prefix="/api")
app.include_router(gardens.router, prefix="/api")
app.include_router(layouts.router, prefix="/api")
app.include_router(plants.router, prefix="/api")
app.include_router(plans.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "JakeGPT"}
