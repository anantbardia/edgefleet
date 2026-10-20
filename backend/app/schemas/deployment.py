"""Deployment schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DeploymentCreate(BaseModel):
    """Create a deployment job."""
    device_ids: List[str] = Field(min_length=1, max_length=50)
    release_id: str
    confirmation_token: str = Field(
        min_length=1,
        description="Token from preflight check to confirm deployment"
    )


class PreflightRequest(BaseModel):
    """Preflight compatibility check request."""
    device_ids: List[str] = Field(min_length=1, max_length=50)
    release_id: str


class PreflightResult(BaseModel):
    """Preflight check result for a single device."""
    device_id: str
    compatible: bool
    warnings: List[str] = []
    errors: List[str] = []


class PreflightResponse(BaseModel):
    """Preflight check response."""
    results: List[PreflightResult]
    all_compatible: bool
    confirmation_token: str = Field(description="Token to confirm deployment")


class DeploymentResponse(BaseModel):
    """Deployment job details."""
    id: str
    device_id: str
    release_id: str
    rollout_id: Optional[str] = None
    state: str
    source_version: Optional[str] = None
    target_version: str
    requested_by: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    verification_evidence: Optional[Dict[str, Any]] = None
    progress_details: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class DeploymentAuditResponse(BaseModel):
    """Deployment audit event."""
    id: int
    deployment_id: str
    timestamp: datetime
    event_type: str
    old_state: Optional[str] = None
    new_state: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class CancelRequest(BaseModel):
    """Deployment cancellation request."""
    reason: str = Field(default="Operator cancelled", max_length=500)
