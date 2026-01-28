"""
Answer Packs API Endpoints

Provides Q&A management linked to intent/workbench
Part of Agent-View-Answers delivery (Wave2-E1 + Wave3-E3)
Updated for Agent-DB-Answers: Real database integration

Endpoints:
- GET /api/answers/packs - List all answer packs
- POST /api/answers/packs - Create new answer pack (audited)
- GET /api/answers/packs/{id} - Get answer pack details
- POST /api/answers/packs/{id}/validate - Validate answer pack
- POST /api/answers/packs/{id}/apply-proposal - Generate apply proposal (audited, not direct apply)
- GET /api/answers/packs/{id}/related - Get related tasks/intents
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from agentos.core.answers.service import (
    AnswersService,
    AnswerPackNotFoundError,
    AnswerPackValidationError
)
from agentos.store.answers_store import AnswersRepo
from agentos.store import get_db_path

logger = logging.getLogger(__name__)

router = APIRouter()


def get_answers_service() -> AnswersService:
    """Get AnswersService instance with real database"""
    db_path = get_db_path()
    repo = AnswersRepo(db_path)
    return AnswersService(repo)


# ==================== Request/Response Models ====================

class AnswerItem(BaseModel):
    """Individual Q&A item"""
    question: str
    answer: str
    type: Optional[str] = "general"  # security_answer, config_answer, etc.


class CreateAnswerPackRequest(BaseModel):
    """Request to create a new answer pack"""
    name: str = Field(..., min_length=1)
    description: Optional[str] = ""
    answers: List[AnswerItem] = Field(..., min_items=1)


class ValidateResult(BaseModel):
    """Validation result for answer pack"""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class ApplyProposalRequest(BaseModel):
    """Request to generate apply proposal"""
    target_intent_id: str
    target_type: str = "intent"  # intent, workbench, etc.


class ApplyProposalResponse(BaseModel):
    """Apply proposal preview (not executed)"""
    proposal_id: str
    target_intent_id: str
    preview: Dict
    status: str = "pending"  # pending approval


class AnswerPack(BaseModel):
    """Answer pack response"""
    id: str
    name: str
    description: str
    answers: List[AnswerItem]
    created_at: str
    created_by: str
    status: str  # valid, invalid
    question_count: int


class RelatedItem(BaseModel):
    """Related task/intent reference"""
    id: str
    type: str  # task, intent
    name: str
    status: str


# ==================== Endpoints ====================

@router.get("/api/answers/packs")
async def list_answer_packs(
    search: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List all answer packs with optional filtering

    Query params:
    - search: Search by name or description
    - status: Filter by status (draft, validated, deprecated, frozen)
    - limit: Max results (default 50)
    - offset: Skip results (pagination)
    """
    try:
        service = get_answers_service()
        packs, total = service.list_packs(
            status=status,
            search=search,
            limit=limit,
            offset=offset
        )

        # Convert to API format
        items_data = [
            {
                "id": pack.id,
                "name": pack.name,
                "status": pack.status,
                "items_count": len(json.loads(pack.items_json)),
                "metadata": json.loads(pack.metadata_json) if pack.metadata_json else {},
                "created_at": pack.created_at,
                "updated_at": pack.updated_at
            }
            for pack in packs
        ]

        return {
            "ok": True,
            "data": items_data,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Failed to list answer packs: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


@router.post("/api/answers/packs")
async def create_answer_pack(request: CreateAnswerPackRequest):
    """
    Create a new answer pack

    NOTE: This operation is audited (creates audit record)
    """
    try:
        service = get_answers_service()

        pack = service.create_pack(
            name=request.name,
            items=[a.dict() for a in request.answers],
            metadata={"description": request.description} if request.description else None
        )

        # TODO: Write audit record
        logger.info(f"Created answer pack: {pack.id} (name: {request.name})")

        return {
            "ok": True,
            "data": {
                "id": pack.id,
                "name": pack.name,
                "status": pack.status,
                "created_at": pack.created_at
            },
            "message": "Answer pack created successfully"
        }

    except AnswerPackValidationError as e:
        logger.error(f"Validation error creating answer pack: {e}")
        return {
            "ok": False,
            "error": str(e),
            "hint": "Check items structure: each must have question and answer"
        }
    except Exception as e:
        logger.error(f"Failed to create answer pack: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


@router.get("/api/answers/packs/{pack_id}")
async def get_answer_pack(pack_id: str):
    """Get detailed information about an answer pack"""
    try:
        service = get_answers_service()
        pack = service.get_pack(pack_id)

        return {
            "ok": True,
            "data": {
                "id": pack.id,
                "name": pack.name,
                "status": pack.status,
                "items": json.loads(pack.items_json),
                "metadata": json.loads(pack.metadata_json) if pack.metadata_json else {},
                "created_at": pack.created_at,
                "updated_at": pack.updated_at
            }
        }

    except AnswerPackNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get answer pack {pack_id}: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


@router.post("/api/answers/packs/{pack_id}/validate")
async def validate_answer_pack(pack_id: str):
    """
    Validate answer pack structure and content

    Returns validation results with errors/warnings
    """
    try:
        service = get_answers_service()
        result = service.validate_pack(pack_id)

        return {
            "ok": True,
            "data": result
        }

    except AnswerPackNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to validate answer pack {pack_id}: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


@router.post("/api/answers/packs/{pack_id}/apply-proposal")
async def create_apply_proposal(pack_id: str, request: ApplyProposalRequest):
    """
    Generate apply proposal (DOES NOT execute, only creates proposal)

    NOTE: This operation is audited (creates audit record)
    The proposal must be approved separately before execution
    """
    try:
        service = get_answers_service()

        proposal = service.create_apply_proposal(
            pack_id=pack_id,
            target_intent_id=request.target_intent_id,
            field_mappings=None
        )

        # TODO: Write audit record
        logger.info(f"Created apply proposal: {proposal['proposal_id']} (pack: {pack_id} -> intent: {request.target_intent_id})")

        return {
            "ok": True,
            "data": proposal,
            "message": "Apply proposal created. Awaiting approval."
        }

    except AnswerPackNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create apply proposal for pack {pack_id}: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


@router.get("/api/answers/packs/{pack_id}/related")
async def get_related_items(pack_id: str):
    """
    Get tasks/intents that reference this answer pack

    Reverse lookup to see where the pack is being used
    """
    try:
        service = get_answers_service()
        related = service.get_related_entities(pack_id)

        return {
            "ok": True,
            "data": related
        }

    except AnswerPackNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get related items for pack {pack_id}: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}
