from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth import get_current_tenant
from app.database import get_db
from app.models import Tenant, Widget
from app.schemas import EmbedSnippetOut, WidgetConfigOut

router = APIRouter(tags=["embed"])

# Bumped whenever the widget.js loader itself changes. Independent of any
# single widget's bundle_version -- this is the "release" the brief's
# versioned-bundle requirement refers to.
SCRIPT_VERSION = 1

WIDGET_JS = """\
(function () {
  var script = document.currentScript;
  var params = new URLSearchParams(script.src.split("?")[1] || "");
  var widgetId = params.get("id");
  var apiBase = script.src.split("/widget.js")[0];
  if (!widgetId) return;

  fetch(apiBase + "/widgets/" + widgetId + "/config")
    .then(function (r) { return r.json(); })
    .then(function (config) { renderWidget(config); })
    .catch(function () { /* config fetch failed -- fail silently, never break the host page */ });

  function renderWidget(config) {
    var container = document.createElement("div");
    container.className = "flyrank-widget flyrank-widget--" + config.type;

    var title = document.createElement("h3");
    title.textContent = config.title;
    container.appendChild(title);

    if (config.description) {
      var desc = document.createElement("p");
      desc.textContent = config.description;
      container.appendChild(desc);
    }

    var form = document.createElement("form");
    (config.fields || []).forEach(function (field) {
      var label = document.createElement("label");
      label.textContent = field.label;
      var input = document.createElement("input");
      input.name = field.name;
      input.type = field.type || "text";
      if (field.required) input.required = true;
      label.appendChild(input);
      form.appendChild(label);
    });

    // Honeypot: a hidden field real visitors never see or fill; bots that
    // fill every input blind will trip it server-side.
    var honeypot = document.createElement("input");
    honeypot.name = "website";
    honeypot.style.display = "none";
    honeypot.tabIndex = -1;
    honeypot.autocomplete = "off";
    form.appendChild(honeypot);

    var submit = document.createElement("button");
    submit.type = "submit";
    submit.textContent = config.button_text || "Submit";
    form.appendChild(submit);

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var data = {};
      new FormData(form).forEach(function (value, key) { data[key] = value; });
      var website = data.website;
      delete data.website;
      fetch(apiBase + "/submissions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ widget_id: widgetId, data: data, website: website })
      }).then(function () {
        container.innerHTML = "<p>Thanks!</p>";
      });
    });

    container.appendChild(form);
    script.parentNode.insertBefore(container, script);
  }
})();
"""


@router.get("/widgets/{widget_id}/embed", response_model=EmbedSnippetOut)
def get_embed_snippet(
    widget_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    widget = db.get(Widget, widget_id)
    if widget is None or widget.tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")
    snippet = (
        f'<script src="/widget.js?id={widget_id}&v={SCRIPT_VERSION}"></script>'
    )
    return EmbedSnippetOut(widget_id=widget_id, snippet=snippet)


@router.get("/widgets/{widget_id}/config", response_model=WidgetConfigOut)
def get_widget_config(widget_id: str, db: Session = Depends(get_db), response: Response = None):
    widget = db.get(Widget, widget_id)
    if widget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")
    # Short-lived cache -- an owner editing a widget should see the change
    # live within seconds, unlike the long-cached script bundle.
    response.headers["Cache-Control"] = "public, max-age=30"
    return widget


@router.get("/widget.js")
def get_widget_js(v: int = SCRIPT_VERSION):
    return Response(
        content=WIDGET_JS,
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
