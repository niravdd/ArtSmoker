/**
 * Safe HTML templating — escaping by construction.
 *
 * Use the `html` tagged template anywhere you build markup for innerHTML:
 *
 *     el.innerHTML = html`<h3>${style.name}</h3>`;   // style.name is auto-escaped
 *
 * Every interpolated value is HTML-escaped by DEFAULT, so untrusted data
 * (asset/style/model names, prompts, filenames, user text) can never inject
 * markup or script — this is stored-XSS-safe even in the multi-user deployment.
 *
 * When an interpolation is itself trusted markup, mark it so it is NOT escaped:
 *   - a nested `html\`...\`` result (a SafeHtml) is inserted as-is,
 *   - an Array of SafeHtml/strings is rendered and joined (great for `.map(...)`),
 *   - `raw(str)` wraps a string you KNOW is safe HTML (use sparingly, never with
 *     user data).
 *
 * Failure mode is safe: if you forget to mark real markup, it shows up escaped
 * (a visible bug), not executed (a security hole).
 *
 * No build step — this file is a plain global (window.html / window.raw /
 * window.escapeHtml), loaded before the components in index.html.
 */
(function () {
  "use strict";

  var ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;", "`": "&#96;" };

  function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value).replace(/[&<>"'`]/g, function (c) { return ESCAPES[c]; });
  }

  // Marker for pre-trusted markup that must NOT be escaped.
  function SafeHtml(htmlString) { this.html = htmlString; }
  SafeHtml.prototype.toString = function () { return this.html; };

  function raw(value) {
    if (value instanceof SafeHtml) return value;
    return new SafeHtml(value === null || value === undefined ? "" : String(value));
  }

  // Render one interpolated value: SafeHtml → as-is; Array → render+join each
  // element; everything else → escaped.
  function render(value) {
    if (value instanceof SafeHtml) return value.html;
    if (Array.isArray(value)) {
      var out = "";
      for (var i = 0; i < value.length; i++) out += render(value[i]);
      return out;
    }
    return escapeHtml(value);
  }

  // Tagged template. Returns a SafeHtml (composable), which coerces to the HTML
  // string when assigned to innerHTML / insertAdjacentHTML.
  function html(strings, ...values) {
    var out = strings[0];
    for (var i = 0; i < values.length; i++) out += render(values[i]) + strings[i + 1];
    return new SafeHtml(out);
  }

  var api = { html: html, raw: raw, escapeHtml: escapeHtml, SafeHtml: SafeHtml };
  if (typeof window !== "undefined") {
    window.html = html;
    window.raw = raw;
    window.escapeHtml = escapeHtml;
    window.SafeHtml = SafeHtml;
  }
  if (typeof module !== "undefined" && module.exports) module.exports = api; // for Node unit tests
})();
