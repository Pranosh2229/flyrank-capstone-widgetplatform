// Shared across every page of this demo "customer site" so the widget id
// only has to be passed once (?widget_id=...) and then persists via
// localStorage while you click between pages -- purely a demo convenience,
// not part of the graded capstone behavior.
(function () {
  var API_BASE = "http://localhost:8000";
  var fromQuery = new URLSearchParams(location.search).get("widget_id");
  if (fromQuery) {
    try { localStorage.setItem("flyrank_demo_widget_id", fromQuery); } catch (e) {}
  }
  var widgetId = fromQuery || (function () {
    try { return localStorage.getItem("flyrank_demo_widget_id"); } catch (e) { return null; }
  })() || "REPLACE_WITH_SEEDED_WIDGET_ID";

  document.write(
    '<script src="' + API_BASE + '/widget.js?id=' + widgetId + '&v=1"><' + '/script>'
  );
})();
