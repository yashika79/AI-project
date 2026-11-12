from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as core_router
from app.api.scheduling_routes import router as scheduling_router
from app.api.rules_routes import router as rules_router
from app.api.agent_routes import router as agent_router
from app.api.rag_routes import router as rag_router
from app.api.evaluation_routes import router as evaluation_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from scripts.seed_demo import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema and seed inventory are available on startup
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Intelligent University Event Planner with State-Space Search, Venue Rules, Multi-Agent Coordination, AI Evaluation, and Policy RAG.",
    lifespan=lifespan,
)

# Include API Routers
app.include_router(core_router)
app.include_router(scheduling_router)
app.include_router(rules_router)
app.include_router(agent_router)
app.include_router(rag_router)
app.include_router(evaluation_router)

# Mount Static Files and Web UI
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", include_in_schema=False)
def serve_dashboard():
    """Serves the interactive web UI dashboard."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": f"Welcome to {settings.APP_NAME}. Visit /docs for OpenAPI specifications."}


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME, "version": "1.0.0"}
