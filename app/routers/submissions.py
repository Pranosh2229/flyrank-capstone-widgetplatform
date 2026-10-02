import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.geo import enrich_ip
from app.models import Submission, Widget
from app.notify import send_confirmation
from app.rate_limit import ip_limiter, widget_limiter
from app.schemas import SubmissionCreate, SubmissionOut

router = APIRouter(tags=["submissions"])

MAX_PAYLOAD_BYTES = 10_000
MAX_FIELD_VALUE_LENGTH = 2_000


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/submissions", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
def create_submission(
    payload: SubmissionCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    ip = _client_ip(request)

    if not ip_limiter.allow(ip, settings.rate_limit_per_ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
    if not widget_limiter.allow(payload.widget_id, settings.rate_limit_per_widget):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")

    widget = db.get(Widget, payload.widget_id)
    if widget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")

    raw_size = len(json.dumps(payload.data).encode("utf-8"))
    if raw_size > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Payload too large")
    for key, value in payload.data.items():
        if isinstance(value, str) and len(value) > MAX_FIELD_VALUE_LENGTH:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Field '{key}' too long")

    allowed_names = {f["name"] for f in widget.fields}
    for key in payload.data.keys():
        if key not in allowed_names:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown field '{key}'")
    for field in widget.fields:
        if field.get("required") and not payload.data.get(field["name"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field '{field['name']}'",
            )

    # Honeypot: a real visitor never sees or fills this field; a bot filling
    # every input blind will. Drop silently -- the response still looks
    # like a normal success so the bot learns nothing.
    if payload.website:
        return SubmissionOut(
            id=str(uuid.uuid4()),
            widget_id=widget.id,
            data=payload.data,
            country=None,
            city=None,
            geo_provider=None,
            status="rejected_spam",
            created_at=datetime.now(timezone.utc),
        )

    if payload.idempotency_key:
        existing = (
            db.query(Submission)
            .filter(
                Submission.widget_id == widget.id,
                Submission.idempotency_key == payload.idempotency_key,
            )
            .first()
        )
        if existing:
            return existing

    country, city, provider = enrich_ip(ip)

    submission = Submission(
        widget_id=widget.id,
        tenant_id=widget.tenant_id,
        data=payload.data,
        ip_address=ip,
        country=country,
        city=city,
        geo_provider=provider,
        idempotency_key=payload.idempotency_key,
        status="stored",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Safe side effect: scheduled after the response is prepared, off the
    # request path, and its failure can never undo the commit above.
    background_tasks.add_task(send_confirmation, submission.id, widget.id)

    return submission
