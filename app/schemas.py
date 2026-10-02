from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class WidgetField(BaseModel):
    name: str
    label: str
    type: str = "text"
    required: bool = False


class WidgetCreate(BaseModel):
    type: str = Field(pattern="^(signup_form|cta|popover)$")
    title: str
    description: str = ""
    fields: list[WidgetField]
    button_text: str = "Submit"
    display_options: dict[str, Any] = {}


class WidgetUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    fields: Optional[list[WidgetField]] = None
    button_text: Optional[str] = None
    display_options: Optional[dict[str, Any]] = None


class WidgetOut(BaseModel):
    id: str
    tenant_id: str
    type: str
    title: str
    description: str
    fields: list[dict]
    button_text: str
    display_options: dict
    bundle_version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WidgetConfigOut(BaseModel):
    id: str
    type: str
    title: str
    description: str
    fields: list[dict]
    button_text: str
    display_options: dict
    bundle_version: int

    class Config:
        from_attributes = True


class EmbedSnippetOut(BaseModel):
    widget_id: str
    snippet: str


class SubmissionCreate(BaseModel):
    widget_id: str
    data: dict[str, Any]
    idempotency_key: Optional[str] = None
    # honeypot field: a real visitor never fills this; a bot that fills every
    # field blind will.
    website: Optional[str] = ""


class SubmissionOut(BaseModel):
    id: str
    widget_id: str
    data: dict
    country: Optional[str]
    city: Optional[str]
    geo_provider: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class StatsOut(BaseModel):
    widget_id: Optional[str]
    total_submissions: int
    by_day: dict[str, int]
    by_country: dict[str, int]
