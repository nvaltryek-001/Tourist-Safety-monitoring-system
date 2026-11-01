"""Smart Tourist Safety Monitoring & AI-Based Incident Intelligence — API."""

from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.bootstrap import bootstrap_staff
from app.core.config import get_settings
from app.database import SessionLocal, engine
from app.migrations import run_migrations
from app.routers import admin, auth, incidents, legacy, me, operations, zones

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.validate()
    if os.getenv("SKIP_MIGRATIONS", "").lower() != "true":
        report = run_migrations(engine)
        log.info("schema v%s ready (from v%s); new tables=%s", report["to_version"], report["from_version"],
                 len(report["new_tables"]))
    db = SessionLocal()
    try:
        bootstrap_staff(db)
    finally:
        db.close()
    yield


settings = get_settings()

app = FastAPI(
    title="Smart Tourist Safety Monitoring API",
    description=(
        "Tourist GPS tracking with consent, geofencing, SOS incident management, "
        "role-based dashboards and explainable safety intelligence."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path not in {"/health", "/ready"}:
        log.info("%s %s -> %s %.1fms id=%s", request.method, request.url.path, response.status_code, elapsed, request_id)
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(p) for p in e.get("loc", []) if p != "body"), "message": e.get("msg")}
        for e in exc.errors()
    ]
    return JSONResponse({"detail": "Validation failed", "errors": errors}, status_code=422)


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


for module in (legacy, auth, me, zones, incidents, admin, operations):
    app.include_router(module.router)
