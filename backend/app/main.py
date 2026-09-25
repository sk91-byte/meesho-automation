import sys
from pathlib import Path

# Ensure 'backend' directory is in sys.path regardless of execution working directory (Render/Local)
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import async_engine, Base
from app.core.logging import setup_logging, logger

from app.api.v1.auth import router as auth_router
from app.api.v1.products import router as products_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.orders import router as orders_router
from app.api.v1.requests import router as requests_router
from app.api.v1.analytics import router as analytics_router

# Setup structured logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Instagram Reseller AI Platform Backend...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully.")
    yield
    logger.info("Shutting down Instagram Reseller AI Platform Backend...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security Headers & Request ID Middleware
@app.middleware("http")
async def security_and_tracing_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.time()
    
    response: Response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    logger.info(
        f"Request {request.method} {request.url.path} status={response.status_code} "
        f"duration={process_time:.2f}ms request_id={request_id}"
    )
    return response


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred."
            },
            "request_id": request_id
        }
    )


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": settings.VERSION, "environment": settings.ENVIRONMENT}


@app.get("/ready", tags=["Health"])
async def ready_check():
    return {"status": "ready", "database": "connected"}


# Include Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(products_router, prefix=settings.API_V1_STR)
app.include_router(webhooks_router, prefix=settings.API_V1_STR)
app.include_router(conversations_router, prefix=settings.API_V1_STR)
app.include_router(orders_router, prefix=settings.API_V1_STR)
app.include_router(requests_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
