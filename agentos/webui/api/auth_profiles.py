"""Auth Profiles API - Read-only Git authentication profile management

Provides REST API for viewing and validating auth profiles (SSH/PAT/netrc).
All write operations (add/remove) are CLI-only for security reasons.

Created for Wave 1-A7: Auth profiles API (read-only)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from agentos.core.git.credentials import (
    CredentialsManager,
    AuthProfileType,
    ValidationStatus,
)
from agentos.core.git.client import GitClientWithAuth

router = APIRouter(prefix="/api/auth/profiles", tags=["auth"])


class ProfileListResponse(BaseModel):
    """Auth profile list response"""
    profiles: List[Dict[str, Any]]
    total: int
    cli_hint: str = "To add/remove auth profiles, use CLI: agentos auth add/remove"


class ProfileDetailResponse(BaseModel):
    """Auth profile detail response"""
    profile: Dict[str, Any]
    cli_hint: str = "To modify this profile, use CLI: agentos auth add/remove"


def mask_credentials(profile_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Mask sensitive credential data"""
    masked = profile_dict.copy()

    # SSH key: hide passphrase
    if "ssh_passphrase" in masked:
        masked["ssh_passphrase"] = "***" if masked["ssh_passphrase"] else None

    # PAT token: show first 4 chars only
    if "token" in masked and masked["token"]:
        token = masked["token"]
        masked["token"] = f"{token[:4]}...{'*' * 36}" if len(token) >= 4 else "***"

    # Netrc password: hide completely
    if "netrc_password" in masked and masked["netrc_password"]:
        masked["netrc_password"] = "***"

    return masked


@router.get("", response_model=ProfileListResponse)
async def list_profiles(
    profile_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
) -> ProfileListResponse:
    """List auth profiles with credential masking"""
    try:
        manager = CredentialsManager()
        profiles = manager.list_profiles(include_sensitive=False)
        profile_dicts = [mask_credentials(p.to_dict(include_sensitive=False)) for p in profiles]

        if profile_type:
            profile_dicts = [p for p in profile_dicts if p["profile_type"] == profile_type]

        return ProfileListResponse(
            profiles=profile_dicts[:limit],
            total=len(profile_dicts),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{profile_name}", response_model=ProfileDetailResponse)
async def get_profile(profile_name: str) -> ProfileDetailResponse:
    """Get auth profile details with credential masking"""
    try:
        manager = CredentialsManager()
        profile = manager.get_profile(profile_name)

        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile not found: {profile_name}")

        return ProfileDetailResponse(
            profile=mask_credentials(profile.to_dict(include_sensitive=False)),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
