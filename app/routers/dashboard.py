from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_tenant
from app.database import get_db
from app.models import Submission, Tenant, Widget
from app.schemas import StatsOut, SubmissionOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/submissions", response_model=list[SubmissionOut])
def list_submissions(
    widget_id: Optional[str] = None,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    query = db.query(Submission).filter(Submission.tenant_id == tenant.id)
    if widget_id:
        query = query.filter(Submission.widget_id == widget_id)
    return query.order_by(Submission.created_at.desc()).all()


@router.get("/widgets/{widget_id}/stats", response_model=StatsOut)
def widget_stats(
    widget_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    widget = db.get(Widget, widget_id)
    if widget is None or widget.tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")

    submissions = (
        db.query(Submission)
        .filter(Submission.widget_id == widget_id, Submission.status == "stored")
        .all()
    )
    by_day = Counter(s.created_at.date().isoformat() for s in submissions)
    by_country = Counter(s.country or "unknown" for s in submissions)
    return StatsOut(
        widget_id=widget_id,
        total_submissions=len(submissions),
        by_day=dict(by_day),
        by_country=dict(by_country),
    )


@router.get("/stats", response_model=StatsOut)
def overall_stats(tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    submissions = (
        db.query(Submission)
        .filter(Submission.tenant_id == tenant.id, Submission.status == "stored")
        .all()
    )
    by_day = Counter(s.created_at.date().isoformat() for s in submissions)
    by_country = Counter(s.country or "unknown" for s in submissions)
    return StatsOut(
        widget_id=None,
        total_submissions=len(submissions),
        by_day=dict(by_day),
        by_country=dict(by_country),
    )
