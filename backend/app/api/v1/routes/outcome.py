"""
Onboarding Outcome State Machine Routes - M18
BFIU Circular No. 29 — Section 3.2 & 6.3

POST /outcome/create           - Create outcome record from verified session
POST /outcome/{id}/auto-route  - Run auto-routing (APPROVED or PENDING_REVIEW)
POST /outcome/{id}/decide      - Checker approve/reject
POST /outcome/{id}/fallback    - Trigger traditional KYC fallback
GET  /outcome/{id}             - Get outcome for a session
GET  /outcome/queue/pending    - List PENDING_REVIEW queue
GET  /outcome/queue/summary    - Count by state
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.services.outcome_service import (
    create_outcome, transition, auto_route,
    checker_decide, trigger_fallback,
    get_outcome, list_outcomes, get_queue_summary,
    STATES, TRANSITIONS,
)

router = APIRouter(prefix="/outcome", tags=["Onboarding Outcome"])


class CreateOutcomeRequest(BaseModel):
    session_id:       str
    verdict:          str
    confidence:       float
    risk_grade:       str   = "LOW"
    risk_score:       int   = 0
    pep_flag:         bool  = False
    edd_required:     bool  = False
    screening_result: str   = "CLEAR"
    kyc_type:         str   = "SIMPLIFIED"
    full_name:        str   = "N/A"
    agent_id:         str   = "N/A"
    institution_id:   str   = "N/A"


class CheckerDecisionRequest(BaseModel):
    checker_id: str
    decision:   str          # APPROVE | REJECT
    note:       Optional[str] = None


class FallbackRequest(BaseModel):
    reason: str = "EC API unavailable — traditional KYC required"


@router.post("/create", status_code=201, operation_id="outcome_create")
async def create_outcome_record(req: CreateOutcomeRequest):
    """Create initial outcome record in PENDING state."""
    if req.verdict not in ("MATCHED", "REVIEW", "FAILED"):
        raise HTTPException(400, "verdict must be MATCHED, REVIEW, or FAILED")
    record = create_outcome(**req.model_dump())
    if "error" in record:
        raise HTTPException(409, record["error"])
    return {"outcome": record, "bfiu_ref": "BFIU Circular No. 29 — Section 3.2"}


@router.post("/{session_id}/auto-route",  operation_id="outcome_auto_route")
async def run_auto_route(session_id: str):
    """
    Run auto-routing logic.
    LOW risk + CLEAR + no PEP + MATCHED -> APPROVED (instant)
    Anything else -> PENDING_REVIEW (checker queue)
    FAILED / BLOCKED -> REJECTED
    """
    result = auto_route(session_id)
    if not result.get("success"):
        raise HTTPException(422, result.get("error","Auto-route failed"))
    return result


@router.post("/{session_id}/decide",      operation_id="outcome_decide")
async def decide_outcome(session_id: str, req: CheckerDecisionRequest):
    """Checker approves or rejects a PENDING_REVIEW case."""
    result = checker_decide(session_id, req.checker_id, req.decision, req.note)
    if not result.get("success"):
        raise HTTPException(422, result.get("error","Decision failed"))
    return result


@router.post("/{session_id}/fallback",    operation_id="outcome_fallback")
async def trigger_outcome_fallback(session_id: str, req: FallbackRequest):
    """Trigger traditional KYC fallback — EC unavailable or eKYC technically failed."""
    result = trigger_fallback(session_id, req.reason)
    if not result.get("success"):
        raise HTTPException(422, result.get("error","Fallback failed"))
    return result


@router.get("/queue/summary",             operation_id="outcome_queue_summary")
async def outcome_queue_summary():
    """Count of outcomes by state — compliance dashboard feed."""
    summary = get_queue_summary()
    pending_review = summary.get("PENDING_REVIEW", 0)
    return {
        "summary":        summary,
        "pending_review": pending_review,
        "action_required": pending_review > 0,
        "bfiu_ref":       "BFIU Circular No. 29 — Section 6.3",
    }


@router.get("/queue/pending",             operation_id="outcome_queue_pending")
async def outcome_pending_queue(limit: int = Query(50, le=200)):
    """List all outcomes in PENDING_REVIEW state — checker queue."""
    items = list_outcomes("PENDING_REVIEW", limit)
    return {
        "queue":  items,
        "total":  len(items),
        "bfiu_ref": "BFIU Circular No. 29 — Section 6.3",
    }


@router.get("/queue/all",                 operation_id="outcome_queue_all")
async def list_all_outcomes(
    state: Optional[str] = None,
    limit: int = Query(50, le=200),
):
    """List all outcomes optionally filtered by state."""
    if state and state not in STATES:
        raise HTTPException(400, f"Invalid state. Must be one of: {STATES}")
    items = list_outcomes(state, limit)
    return {"outcomes": items, "total": len(items)}


@router.get("/{session_id}",              operation_id="outcome_get")
async def get_outcome_record(session_id: str):
    """Get outcome record for a session."""
    record = get_outcome(session_id)
    if not record:
        raise HTTPException(404, f"No outcome found for session '{session_id}'")
    return {"outcome": record}


@router.get("/states/transitions",        operation_id="outcome_state_transitions")
async def list_state_transitions():
    """Return valid state transition map."""
    return {
        "states":      list(STATES),
        "transitions": TRANSITIONS,
        "auto_approve_criteria": [
            "verdict == MATCHED",
            "risk_grade == LOW",
            "screening_result == CLEAR",
            "pep_flag == False",
            "edd_required == False",
        ],
    }
