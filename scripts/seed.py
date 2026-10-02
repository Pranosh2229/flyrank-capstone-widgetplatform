"""Seed demo data: one tenant + one widget, so a stranger cloning the repo
has something to point the customer-site test page at immediately.

Idempotent -- safe to run again (skips if the demo tenant already exists).
"""

from app.auth import hash_password
from app.database import SessionLocal
from app.models import Tenant, Widget

DEMO_EMAIL = "demo@flyrank.test"
DEMO_PASSWORD = "demopassword123"


def run():
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.email == DEMO_EMAIL).first()
        if tenant:
            print(f"Demo tenant already exists: {DEMO_EMAIL}")
            widget = db.query(Widget).filter(Widget.tenant_id == tenant.id).first()
            if widget:
                print(f"Demo widget id: {widget.id}")
            return

        tenant = Tenant(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        widget = Widget(
            tenant_id=tenant.id,
            type="signup_form",
            title="Join our newsletter",
            description="Get product updates, no spam.",
            fields=[{"name": "email", "label": "Email", "type": "email", "required": True}],
            button_text="Subscribe",
            display_options={"theme": "light"},
        )
        db.add(widget)
        db.commit()
        db.refresh(widget)

        print(f"Seeded demo tenant: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print(f"Seeded demo widget id: {widget.id}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
