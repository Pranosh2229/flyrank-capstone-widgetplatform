import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    widgets = relationship("Widget", back_populates="tenant")


class Widget(Base):
    __tablename__ = "widgets"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id = Column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, default="")
    fields = Column(JSONB, nullable=False, default=list)
    button_text = Column(String, default="Submit")
    display_options = Column(JSONB, nullable=False, default=dict)
    bundle_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    tenant = relationship("Tenant", back_populates="widgets")
    submissions = relationship("Submission", back_populates="widget")


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("widget_id", "idempotency_key", name="uq_submission_idempotency"),
        Index("ix_submissions_widget_id", "widget_id"),
        Index("ix_submissions_tenant_id", "tenant_id"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    widget_id = Column(UUID(as_uuid=False), ForeignKey("widgets.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False)
    data = Column(JSONB, nullable=False, default=dict)
    ip_address = Column(String, nullable=True)
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    geo_provider = Column(String, nullable=True)
    idempotency_key = Column(String, nullable=True)
    status = Column(String, nullable=False, default="stored")
    created_at = Column(DateTime(timezone=True), default=_now, index=True)

    widget = relationship("Widget", back_populates="submissions")
