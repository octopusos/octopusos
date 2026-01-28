"""
Secrets API - Secure API Key Management

Sprint B Task #6: Cloud API Key Configuration
Sprint B Task #7: Added admin token auth protection

Endpoints:
- GET /api/settings/secrets/status - Get configuration status (no keys)
- POST /api/settings/secrets - Save/update API key (requires admin token)
- DELETE /api/settings/secrets/{provider} - Delete API key (requires admin token)

Security:
- Never return actual API keys in responses
- Only return configured status + last-4 digits
- All errors redact keys from messages
- Write operations require admin token authentication
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from agentos.webui.secrets import SecretStore, SecretInfo
from agentos.webui.auth.simple_token import require_admin, security_scheme

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings/secrets")

# Singleton SecretStore instance
_secret_store: SecretStore = None


def get_secret_store() -> SecretStore:
    """Get or create SecretStore singleton"""
    global _secret_store
    if _secret_store is None:
        _secret_store = SecretStore()
    return _secret_store


# Request/Response Models

class SaveSecretRequest(BaseModel):
    """Request to save API key"""
    provider: str = Field(..., description="Provider ID (e.g., 'openai', 'anthropic')")
    api_key: str = Field(..., description="API key to store", min_length=8)


class SecretStatusResponse(BaseModel):
    """Response with secret status (no actual key)"""
    provider: str
    configured: bool
    last4: str = None
    updated_at: str = None


class AllSecretsStatusResponse(BaseModel):
    """Response with all secrets status"""
    secrets: List[SecretStatusResponse]


class SaveSecretResponse(BaseModel):
    """Response after saving secret"""
    ok: bool
    provider: str
    configured: bool
    last4: str = None


class DeleteSecretResponse(BaseModel):
    """Response after deleting secret"""
    ok: bool
    provider: str
    configured: bool


# API Endpoints

@router.get("/status", response_model=AllSecretsStatusResponse)
async def get_all_secrets_status():
    """
    Get configuration status for all providers

    Returns metadata only (never actual keys)
    """
    try:
        store = get_secret_store()
        all_status = store.get_all_status()

        return AllSecretsStatusResponse(
            secrets=[
                SecretStatusResponse(
                    provider=info.provider,
                    configured=info.configured,
                    last4=info.last4,
                    updated_at=info.updated_at,
                )
                for info in all_status
            ]
        )

    except Exception as e:
        logger.error(f"Failed to get secrets status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve secrets status"
        )


@router.get("/status/{provider}", response_model=SecretStatusResponse)
async def get_secret_status(provider: str):
    """
    Get configuration status for specific provider

    Returns metadata only (never actual key)
    """
    try:
        store = get_secret_store()
        info = store.get_status(provider)

        return SecretStatusResponse(
            provider=info.provider,
            configured=info.configured,
            last4=info.last4,
            updated_at=info.updated_at,
        )

    except Exception as e:
        logger.error(f"Failed to get secret status for {provider}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve secret status for {provider}"
        )


@router.post("", response_model=SaveSecretResponse)
async def save_secret(
    request: SaveSecretRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    _auth: bool = Depends(require_admin),
):
    """
    Save or update API key for provider

    Requires admin token authentication.

    Security: Key is stored securely and never returned in response
    """
    try:
        store = get_secret_store()

        # Validate provider
        if request.provider not in ["openai", "anthropic"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {request.provider}"
            )

        # Save secret
        info = store.save_secret(request.provider, request.api_key)

        logger.info(f"API key saved for provider: {request.provider}")

        return SaveSecretResponse(
            ok=True,
            provider=info.provider,
            configured=info.configured,
            last4=info.last4,
        )

    except ValueError as e:
        # Validation errors
        logger.warning(f"Invalid secret request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except PermissionError as e:
        # Permission errors (file access)
        logger.error(f"Permission error saving secret: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Secrets file has insecure permissions. Check server logs for fix instructions."
        )

    except Exception as e:
        # Generic errors (never leak key details)
        logger.error(f"Failed to save secret: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save secret"
        )


@router.delete("/{provider}", response_model=DeleteSecretResponse)
async def delete_secret(
    provider: str,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    _auth: bool = Depends(require_admin),
):
    """
    Delete API key for provider

    Requires admin token authentication.
    """
    try:
        store = get_secret_store()

        # Delete secret
        info = store.delete_secret(provider)

        logger.info(f"API key deleted for provider: {provider}")

        return DeleteSecretResponse(
            ok=True,
            provider=info.provider,
            configured=info.configured,
        )

    except Exception as e:
        logger.error(f"Failed to delete secret for {provider}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete secret for {provider}"
        )
