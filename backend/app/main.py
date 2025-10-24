"""FastAPI main application"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config import settings
from app.api.routes import router as api_router
from app.auth.jwt_handler import create_access_token
from app.api.chat_routes import router as chat_router


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="LogWatch API",
    description="Log Ingestion and Search System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "LogWatch API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    from app.search.client import get_opensearch_client
    
    try:
        client = get_opensearch_client()
        health_info = client.cluster.health()
        return {
            "status": "healthy",
            "opensearch": health_info['status']
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting LogWatch API...")
    logger.info(f"OpenSearch: {settings.opensearch_host}:{settings.opensearch_port}")
    logger.info(f"Auth required: {settings.require_auth}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down LogWatch API...")
