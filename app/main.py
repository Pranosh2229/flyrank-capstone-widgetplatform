from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, dashboard, embed, submissions, widgets

app = FastAPI(title="FlyRank Capstone — Embeddable Widget & Lead-Capture Platform")

allow_origins = (
    ["*"] if settings.cors_allow_origins == "*" else settings.cors_allow_origins.split(",")
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(widgets.router)
app.include_router(embed.router)
app.include_router(submissions.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"status": "ok"}
