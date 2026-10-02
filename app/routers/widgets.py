from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_tenant
from app.database import get_db
from app.models import Tenant, Widget
from app.schemas import WidgetCreate, WidgetOut, WidgetUpdate

router = APIRouter(prefix="/widgets", tags=["widgets"])


def _get_owned_widget(widget_id: str, tenant: Tenant, db: Session) -> Widget:
    widget = db.get(Widget, widget_id)
    # Same 404 whether the widget doesn't exist or belongs to another
    # tenant -- never leak that another tenant's widget id is valid.
    if widget is None or widget.tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")
    return widget


@router.post("", response_model=WidgetOut, status_code=status.HTTP_201_CREATED)
def create_widget(
    payload: WidgetCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    widget = Widget(
        tenant_id=tenant.id,
        type=payload.type,
        title=payload.title,
        description=payload.description,
        fields=[f.model_dump() for f in payload.fields],
        button_text=payload.button_text,
        display_options=payload.display_options,
    )
    db.add(widget)
    db.commit()
    db.refresh(widget)
    return widget


@router.get("", response_model=list[WidgetOut])
def list_widgets(tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    return db.query(Widget).filter(Widget.tenant_id == tenant.id).all()


@router.get("/{widget_id}", response_model=WidgetOut)
def get_widget(
    widget_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return _get_owned_widget(widget_id, tenant, db)


@router.put("/{widget_id}", response_model=WidgetOut)
def update_widget(
    widget_id: str,
    payload: WidgetUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    widget = _get_owned_widget(widget_id, tenant, db)
    data = payload.model_dump(exclude_unset=True)
    if "fields" in data and data["fields"] is not None:
        data["fields"] = [f if isinstance(f, dict) else f.model_dump() for f in payload.fields]
    bumped = False
    for key, value in data.items():
        setattr(widget, key, value)
        if key in ("fields", "title", "button_text", "display_options"):
            bumped = True
    if bumped:
        widget.bundle_version += 1
    db.commit()
    db.refresh(widget)
    return widget


@router.delete("/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_widget(
    widget_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    widget = _get_owned_widget(widget_id, tenant, db)
    db.delete(widget)
    db.commit()
