"""initial schema: tenants, widgets, submissions

Revision ID: 0001
Revises:
Create Date: 2026-10-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("email", sa.String, nullable=False, unique=True),
        sa.Column("password_hash", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_tenants_email", "tenants", ["email"])

    op.create_table(
        "widgets",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("type", sa.String, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("description", sa.String, server_default=""),
        sa.Column("fields", postgresql.JSONB, nullable=False),
        sa.Column("button_text", sa.String, server_default="Submit"),
        sa.Column("display_options", postgresql.JSONB, nullable=False),
        sa.Column("bundle_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_widgets_tenant_id", "widgets", ["tenant_id"])

    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("widget_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("widgets.id"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("data", postgresql.JSONB, nullable=False),
        sa.Column("ip_address", sa.String, nullable=True),
        sa.Column("country", sa.String, nullable=True),
        sa.Column("city", sa.String, nullable=True),
        sa.Column("geo_provider", sa.String, nullable=True),
        sa.Column("idempotency_key", sa.String, nullable=True),
        sa.Column("status", sa.String, nullable=False, server_default="stored"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_submissions_widget_id", "submissions", ["widget_id"])
    op.create_index("ix_submissions_tenant_id", "submissions", ["tenant_id"])
    op.create_index("ix_submissions_created_at", "submissions", ["created_at"])
    op.create_unique_constraint(
        "uq_submission_idempotency", "submissions", ["widget_id", "idempotency_key"]
    )


def downgrade():
    op.drop_table("submissions")
    op.drop_table("widgets")
    op.drop_table("tenants")
