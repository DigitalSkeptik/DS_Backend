from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.api_router import v1_api_router, v2_api_router
from app.core.config import get_settings
from app.core.limiter import limiter

app = FastAPI(
    title="DigitalSkeptik Backend",
    version="0.0.1",
    description="https://github.com/DigitalSkeptik/DS_Backend",
    openapi_url=None,
    docs_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore


v1_app = FastAPI(
    title="DigitalSkeptik Backend v1",
    version="0.0.1",
    description="https://github.com/DigitalSkeptik/DS_Backend",
    openapi_url="/openapi.json",
    docs_url="/docs",
)

v2_app = FastAPI(
    title="DigitalSkeptik Backend v2",
    version="0.0.1",
    description="https://github.com/DigitalSkeptik/DS_Backend",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

v1_app.include_router(v1_api_router)
v2_app.include_router(v2_api_router)

v1_app.state.limiter = limiter
v1_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
v2_app.add_middleware(SlowAPIMiddleware)

v2_app.state.limiter = limiter
v2_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
v2_app.add_middleware(SlowAPIMiddleware)

app.mount("/api/v1", v1_app)
app.mount("/api/v2", v2_app)

# Sets all CORS enabled origins

app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        str(origin).rstrip("/")
        for origin in get_settings().security.backend_cors_origins
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Guards against HTTP Host Header attacks
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=get_settings().security.allowed_hosts,
)
