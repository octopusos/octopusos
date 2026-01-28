"""
FastAPI Application - AgentOS WebUI

Main application entry point for the Web Control Surface

Refactored in v0.3.2 (P1 Sprint):
- Added SessionStore initialization (SQLite persistent storage)
- Added config-based fallback to MemoryStore (degraded mode)
- WebUI data now persists across restarts
- Added Sentry error tracking and performance monitoring
"""

import logging
import os
from pathlib import Path
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

# Import API routers
from agentos.webui.api import health, sessions, tasks, events, skills, memory, config, logs, providers, selfcheck, context, runtime, providers_control, support, secrets, sessions_runtime, providers_lifecycle, providers_instances, knowledge, history, share, preview, snippets, governance, guardians, lead, projects, task_dependencies, governance_dashboard, guardian, content, answers, auth, execution, dryrun, intent, auth_profiles
from agentos.webui.websocket import chat, events as ws_events

# Import SessionStore
from agentos.webui.store import SQLiteSessionStore, MemorySessionStore

logger = logging.getLogger(__name__)

# Initialize Sentry for error tracking, performance monitoring, and release health
# Can be disabled by setting SENTRY_ENABLED=false
SENTRY_ENABLED = os.getenv("SENTRY_ENABLED", "true").lower() == "true"
SENTRY_DSN = os.getenv("SENTRY_DSN", "https://0f4d8d4b457861cad05ed94aa1b53c40@o4510344567586816.ingest.us.sentry.io/4510783131942912")
SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", "development")
SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0"))
SENTRY_PROFILES_SAMPLE_RATE = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "1.0"))
SENTRY_RELEASE = os.getenv("SENTRY_RELEASE", "agentos-webui@0.3.2")

if SENTRY_ENABLED and SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        # Enable FastAPI and Starlette integrations
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
        ],
        # Performance monitoring: 100% in dev, adjust in production
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        # Profiling: 100% in dev, adjust in production
        profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
        # Include request data (headers, cookies, user IP, etc.)
        send_default_pii=True,
        # Environment (development, staging, production)
        environment=SENTRY_ENVIRONMENT,
        # Release version (used for Release Health tracking)
        release=SENTRY_RELEASE,
        # Breadcrumb settings
        max_breadcrumbs=50,
        # Additional options
        attach_stacktrace=True,

        # === Release Health: Auto Session Tracking ===
        # For server-mode applications (FastAPI), sessions are tracked per-request
        # Each HTTP request = 1 session for Release Health metrics
        # Sentry automatically detects the application type and uses request-mode
        auto_session_tracking=True,

        # Filter out healthcheck noise
        before_send=lambda event, hint: (
            None if event.get("request", {}).get("url", "").endswith("/health") else event
        ),

        # Ignore health check transactions in performance monitoring
        traces_sampler=lambda sampling_context: (
            0.0 if sampling_context.get("wsgi_environ", {}).get("PATH_INFO", "").endswith("/health")
            else SENTRY_TRACES_SAMPLE_RATE
        ),
    )
    logger.info(
        f"Sentry initialized: {SENTRY_RELEASE} "
        f"(env: {SENTRY_ENVIRONMENT}, traces: {SENTRY_TRACES_SAMPLE_RATE*100}%, "
        f"profiles: {SENTRY_PROFILES_SAMPLE_RATE*100}%, sessions: enabled)"
    )
else:
    logger.info("Sentry monitoring disabled")

# Get the webui directory path
WEBUI_DIR = Path(__file__).parent
STATIC_DIR = WEBUI_DIR / "static"
TEMPLATES_DIR = WEBUI_DIR / "templates"

# Create FastAPI app
app = FastAPI(
    title="AgentOS WebUI",
    description="Control Surface for AgentOS - Observability & Control",
    version="0.3.2",  # Updated for P1 Sprint
)

# Custom exception handler for HTTPException with our API contract format
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTPException and format according to our API contract

    If the exception detail is a dict with our standard format (ok, error, etc.),
    return it directly. Otherwise, wrap the detail in our format.
    """
    detail = exc.detail

    # If detail is already in our format, return it
    if isinstance(detail, dict) and "ok" in detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=detail
        )

    # Otherwise, wrap it in our format
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "ok": False,
            "data": None,
            "error": str(detail) if detail else "An error occurred",
            "hint": None,
            "reason_code": "INTERNAL_ERROR"
        }
    )

# Register audit middleware (must be before route registration)
from agentos.webui.middleware.audit import add_audit_middleware
add_audit_middleware(app)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Register API routes
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(sessions_runtime.router, tags=["sessions"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(skills.router, prefix="/api/skills", tags=["skills"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])
app.include_router(secrets.router, tags=["secrets"])
app.include_router(providers.router, prefix="/api/providers", tags=["providers"])
app.include_router(providers_control.router, tags=["providers"])
app.include_router(providers_lifecycle.router, tags=["providers"])
app.include_router(providers_instances.router, tags=["providers"])
app.include_router(selfcheck.router, prefix="/api/selfcheck", tags=["selfcheck"])
app.include_router(context.router, prefix="/api/context", tags=["context"])
app.include_router(runtime.router, prefix="/api/runtime", tags=["runtime"])
app.include_router(support.router, prefix="/api/support", tags=["support"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(history.router, prefix="/api/history", tags=["history"])
app.include_router(share.router, prefix="/api", tags=["share"])
app.include_router(preview.router, prefix="/api", tags=["preview"])
app.include_router(snippets.router, prefix="/api/snippets", tags=["snippets"])
app.include_router(governance.router, tags=["governance"])
app.include_router(governance_dashboard.router, tags=["governance_dashboard"])
app.include_router(guardians.router, tags=["guardians"])
app.include_router(guardian.router, tags=["guardian"])
app.include_router(lead.router, tags=["lead"])
app.include_router(projects.router, tags=["projects"])
app.include_router(task_dependencies.router, tags=["tasks"])
app.include_router(content.router, tags=["content"])
app.include_router(execution.router, tags=["execution"])
app.include_router(dryrun.router, tags=["dryrun"])
app.include_router(intent.router, tags=["intent"])
app.include_router(answers.router, tags=["answers"])
app.include_router(auth.router, tags=["auth"])
app.include_router(auth_profiles.router, tags=["auth_profiles"])

# Register WebSocket routes
app.include_router(chat.router, prefix="/ws", tags=["websocket"])
app.include_router(ws_events.router, prefix="/ws", tags=["websocket"])


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main control surface page"""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "AgentOS Control Surface",
            "sentry_environment": SENTRY_ENVIRONMENT,
        }
    )


@app.get("/health-check", response_class=HTMLResponse)
async def health_check_page(request: Request):
    """Health check page for debugging"""
    return templates.TemplateResponse(
        "health.html",
        {"request": request}
    )


@app.get("/share/{share_id}", response_class=HTMLResponse)
async def share_preview_page(request: Request, share_id: str):
    """Shared preview page"""
    return templates.TemplateResponse(
        "share.html",
        {
            "request": request,
            "share_id": share_id
        }
    )


@app.on_event("startup")
async def startup_event():
    """
    Application startup

    Initializes SessionStore:
    - Tries SQLiteSessionStore (persistent)
    - Falls back to MemorySessionStore on error (degraded mode)
    - Configurable via AGENTOS_WEBUI_USE_MEMORY_STORE env var
    """
    logger.info("AgentOS WebUI starting...")
    logger.info(f"Static files: {STATIC_DIR}")
    logger.info(f"Templates: {TEMPLATES_DIR}")

    # Initialize SessionStore
    use_memory = os.getenv("AGENTOS_WEBUI_USE_MEMORY_STORE", "false").lower() == "true"

    if use_memory:
        logger.warning("Using MemorySessionStore (data will not persist)")
        store = MemorySessionStore()
    else:
        try:
            # Get DB path from environment or use default
            db_path = os.getenv("AGENTOS_DB_PATH", "store/registry.sqlite")

            # Ensure parent directory exists
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"Initializing SQLiteSessionStore: {db_path}")
            store = SQLiteSessionStore(db_path)
            logger.info("SQLiteSessionStore initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SQLiteSessionStore: {e}")
            logger.warning("Falling back to MemorySessionStore (degraded mode)")
            store = MemorySessionStore()

    # Inject store into sessions API
    sessions.set_session_store(store)
    logger.info(f"SessionStore injected: {type(store).__name__}")

    # Ensure "main" session exists for backward compatibility
    try:
        if store.get_session("main") is None:
            logger.info("Creating default 'main' session")
            main_session = store.create_session(
                session_id="main",
                user_id="default",
                metadata={"title": "Main Session", "tags": ["default"]}
            )
            logger.info(f"Created main session: {main_session.session_id}")
    except Exception as e:
        logger.warning(f"Failed to create main session: {e}")

    # Cleanup stale KB index jobs on startup
    try:
        from agentos.webui.api.knowledge import cleanup_stale_jobs, CleanupJobsRequest
        result = await cleanup_stale_jobs(CleanupJobsRequest(older_than_hours=1))
        if result.cleaned_count > 0:
            logger.info(f"Cleaned {result.cleaned_count} stale KB index jobs on startup")
    except Exception as e:
        logger.warning(f"Failed to cleanup stale jobs on startup: {e}")

    # Retry failed KB index jobs on startup
    try:
        from agentos.webui.api.knowledge import retry_failed_jobs, RetryFailedJobsRequest
        result = await retry_failed_jobs(RetryFailedJobsRequest(max_retries=1, hours_lookback=24))
        if result.retried_count > 0:
            logger.info(f"Retrying {result.retried_count} failed KB index jobs on startup (skipped {result.skipped_count})")
        elif result.skipped_count > 0:
            logger.info(f"Found {result.skipped_count} failed jobs, but all were already retried or too old")
    except Exception as e:
        logger.warning(f"Failed to retry failed jobs on startup: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("AgentOS WebUI shutting down...")
