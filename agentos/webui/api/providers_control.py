"""
Provider Control API - Start/Stop lifecycle management

Sprint B Task #5: Ollama 启停 API
Sprint B Task #7: Added admin token auth protection

Endpoints:
- POST /api/providers/ollama/start (requires admin token)
- POST /api/providers/ollama/stop (requires admin token)
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any

from agentos.providers.ollama_controller import OllamaController
from agentos.webui.auth.simple_token import require_admin, security_scheme

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/providers")


# Response model (matches ControlResult structure)
class ControlResponse(BaseModel):
    ok: bool
    provider: str
    action: str
    state: str
    pid: Optional[int] = None
    message: str
    error: Optional[Dict[str, str]] = None


@router.post("/ollama/start", response_model=ControlResponse)
async def start_ollama(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    _auth: bool = Depends(require_admin),
):
    """
    Start Ollama server (idempotent)

    Requires admin token authentication.

    Returns:
        ControlResponse with ok=True if started or already running
    """
    logger.info("API: Start Ollama request received")

    try:
        controller = OllamaController()
        result = controller.start()

        # Convert ControlResult to response dict
        response = ControlResponse(
            ok=result.ok,
            provider=result.provider,
            action=result.action,
            state=result.state,
            pid=result.pid,
            message=result.message,
            error=result.error,
        )

        logger.info(f"API: Start Ollama result - ok={result.ok}, state={result.state}")
        return response

    except Exception as e:
        logger.error(f"API: Start Ollama failed with exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ollama/stop", response_model=ControlResponse)
async def stop_ollama(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    _auth: bool = Depends(require_admin),
):
    """
    Stop Ollama server (idempotent)

    Requires admin token authentication.

    Returns:
        ControlResponse with ok=True if stopped or already stopped
    """
    logger.info("API: Stop Ollama request received")

    try:
        controller = OllamaController()
        result = controller.stop()

        # Convert ControlResult to response dict
        response = ControlResponse(
            ok=result.ok,
            provider=result.provider,
            action=result.action,
            state=result.state,
            pid=result.pid,
            message=result.message,
            error=result.error,
        )

        logger.info(f"API: Stop Ollama result - ok={result.ok}, state={result.state}")
        return response

    except Exception as e:
        logger.error(f"API: Stop Ollama failed with exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
