from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting Football RAG API...")
    print("📂 Initializing ChromaDB and loading documents...")
    print("✅ Initialization complete. Ready to serve requests!")
    yield
    print("👋 Shutting down Football RAG API...")


app = FastAPI(
    title="Football RAG API",
    description="Semantic search over football tactics documents",
    version="1.0.0",
    docs_url="/football-docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")  # Ensure the root endpoint is registered
async def root():
    return {
        "message": "🏃 Football RAG API is running!",
        "docs": "/docs",
        "endpoints": {
            "search": "POST /api/v1/search",
            "health": "GET /api/v1/health"
        }
    }