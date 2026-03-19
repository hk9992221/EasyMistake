import asyncio
import logging
import os
import traceback
import uuid
from contextlib import asynccontextmanager, suppress
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from api.core.config import settings
from api.core.exceptions import AppException
from api.core.error_codes import ErrorCode
from api.core.database import get_db
from api.core.jobs import fetch_next_job
from api.models.job import JobType
from api.worker import ExportWorker
from api.api.v1 import (
    auth,
    questions,
    extractions,
    paper_sets,
    exports,
    jobs,
    images,
    papers,
    attempts,
    admin,
    question_progress,
    reviews,
    analytics,
    simple_grading,
)


async def _embedded_export_worker_loop(worker_id: str):
    logger = logging.getLogger("uvicorn.error")
    worker = ExportWorker(worker_id)
    logger.info("Embedded export worker started: %s", worker_id)

    while True:
        try:
            async for db in get_db():
                await worker.maintenance_tick(db)
                job = await fetch_next_job(db, worker_id=worker_id, job_types=[JobType.EXPORT])
                if job:
                    await worker.process_job(db, job)
                else:
                    break
        except asyncio.CancelledError:
            logger.info("Embedded export worker stopping: %s", worker_id)
            raise
        except Exception as exc:
            logger.exception("Error in embedded export worker loop: %s", exc)

        await asyncio.sleep(settings.EXPORT_WORKER_POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task: asyncio.Task | None = None
    if settings.EXPORT_WORKER_AUTO_START:
        worker_id = f"embedded-worker-{os.getpid()}"
        worker_task = asyncio.create_task(_embedded_export_worker_loop(worker_id))

    try:
        yield
    finally:
        if worker_task:
            worker_task.cancel()
            with suppress(asyncio.CancelledError):
                await worker_task


app = FastAPI(
    title="MistakeDev API",
    description="Question management API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    request_id = str(uuid.uuid4())
    details = exc.detail if isinstance(exc.detail, list) else None
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": message, "details": details, "request_id": request_id},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = str(uuid.uuid4())
    code = ErrorCode.BAD_REQUEST
    if exc.status_code == 401:
        code = ErrorCode.UNAUTHORIZED
    elif exc.status_code == 403:
        code = ErrorCode.FORBIDDEN
    elif exc.status_code == 404:
        code = ErrorCode.NOT_FOUND
    elif exc.status_code == 409:
        code = ErrorCode.CONFLICT

    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    details = exc.detail if isinstance(exc.detail, list) else None
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": code, "message": message, "details": details, "request_id": request_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = str(uuid.uuid4())
    errors = jsonable_encoder(exc.errors())
    details = []
    for item in errors:
        loc = item.get("loc", [])
        field = ".".join(str(x) for x in loc[1:]) if len(loc) > 1 else ".".join(str(x) for x in loc)
        details.append({"field": field, "reason": item.get("msg", "invalid")})
    return JSONResponse(
        status_code=422,
        content={
            "code": ErrorCode.VALIDATION_ERROR,
            "message": "Validation error",
            "details": details,
            "request_id": request_id,
            "errors": errors,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = str(uuid.uuid4())
    logger = logging.getLogger("uvicorn.error")
    logger.error("Unhandled exception: %s", exc)
    logger.debug("Traceback:\n%s", "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    message = "Internal Server Error"
    if settings.ENVIRONMENT == "development":
        message = str(exc)
    return JSONResponse(
        status_code=500,
        content={"code": ErrorCode.INTERNAL_ERROR, "message": message, "request_id": request_id},
    )


app.include_router(auth.router, prefix="/api/v1")
app.include_router(questions.router, prefix="/api/v1")
app.include_router(extractions.router, prefix="/api/v1")
app.include_router(images.router, prefix="/api/v1")
app.include_router(paper_sets.router, prefix="/api/v1")
app.include_router(exports.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(papers.router, prefix="/api/v1")
app.include_router(attempts.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(question_progress.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(simple_grading.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "message": "MistakeDev API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}

PROXY_STRIP_RESPONSE_HEADERS = {
    "content-encoding",
    "content-length",
}


@app.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_frontend(request: Request, full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")

    target_base = settings.FRONTEND_BASE_URL.rstrip("/")
    target_path = f"/{full_path}" if full_path else "/"
    target_url = f"{target_base}{target_path}"
    if request.query_params:
        target_url = f"{target_url}?{urlencode(list(request.query_params.multi_items()))}"

    request_headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in HOP_BY_HOP_HEADERS and k.lower() not in {"host", "content-length"}
    }
    # Preserve original host/proto info for upstream app while keeping upstream host local.
    request_headers["x-forwarded-host"] = request.headers.get("host", "")
    request_headers["x-forwarded-proto"] = request.headers.get("x-forwarded-proto", request.url.scheme)
    request_headers["accept-encoding"] = "identity"
    if request.client and request.client.host:
        prior = request.headers.get("x-forwarded-for")
        request_headers["x-forwarded-for"] = f"{prior}, {request.client.host}" if prior else request.client.host

    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=60) as client:
            upstream = await client.request(
                method=request.method,
                url=target_url,
                headers=request_headers,
                content=await request.body(),
            )
    except httpx.RequestError:
        return JSONResponse(
            status_code=502,
            content={
                "code": ErrorCode.INTERNAL_ERROR,
                "message": f"Frontend server unavailable at {settings.FRONTEND_BASE_URL}",
            },
        )

    response_headers = {
        k: v
        for k, v in upstream.headers.items()
        if k.lower() not in HOP_BY_HOP_HEADERS and k.lower() not in PROXY_STRIP_RESPONSE_HEADERS
    }
    if "location" in response_headers:
        public_origin = str(request.base_url).rstrip("/")
        response_headers["location"] = response_headers["location"].replace(target_base, public_origin)
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
