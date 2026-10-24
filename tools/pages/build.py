"""Builds guide pages that share twinportals.html's look: its <head> styles, recipe-grid
renderer, and checklist code. Each page is pages/<name>.body.html (the content inside
.wrap) plus optional pages/<name>.recipes.json. Usage: python -I build.py <docs dir> <name>...
A body may contain <!-- include: generated/x.html -->, replaced by that file (see gen_cobblevalley.py).
Cobble Valley (cv-*) and Dev (dev-*) pages also get CV_CSS. tools/pages/make.py rebuilds everything."""
import json, os, re, sys

here = os.path.dirname(os.path.abspath(__file__))
EXTRA_CSS = """
.cslot.empty { background: var(--grid-slot); opacity: 0.55; }
.lineup { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 12px; margin-top: 8px; }
.card { background: var(--slot); border: 2px solid var(--slot-border); padding: 12px 14px; display: flex; flex-direction: column; gap: 6px; }
.card .cname { font-family: "Silkscreen", monospace; font-size: 0.95rem; }
.card .ctag { font-family: "Space Mono", monospace; font-size: 0.72rem; color: var(--accent); }
.card p { margin: 0; font-size: 0.88rem; color: var(--ink-soft); }
.card ul { margin: 0; padding-left: 1.1em; font-size: 0.86rem; color: var(--ink-soft); }
code { font-family: "Space Mono", monospace; font-size: 0.85em; background: var(--slot); border: 1px solid var(--slot-border); padding: 0 4px; }
"""

# Cobble Valley and Dev pages only, so the older pages' output stays byte-identical.
CV_CSS = """
.cv-age { display: inline-block; font-family: "Silkscreen", monospace; font-size: 0.72rem; padding: 2px 8px; border: 2px solid; white-space: nowrap; }
.cv-age-wood { color: #8a4b1f; border-color: #a0522d; background: #f6e7da; }
.cv-age-stone { color: #555; border-color: #8a8a8a; background: #ececec; }
.cv-age-iron { color: #4d4d4d; border-color: #b8b8b8; background: #fafafa; }
.cv-age-diamond { color: #116b62; border-color: #4aedd9; background: #e3fbf8; }
.cv-age-nether { color: #8e2420; border-color: #b02e26; background: #f9e3e1; }
.cv-age-end { color: #6a3d9a; border-color: #c77dff; background: #f3e8ff; }
.cv-age-champion { color: #8a6d00; border-color: #ffd700; background: #fff8d6; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) .cv-age { background: transparent; filter: brightness(1.6); } }
:root[data-theme="dark"] .cv-age { background: transparent; filter: brightness(1.6); }
details { background: var(--slot); border: 2px solid var(--slot-border); padding: 8px 12px; margin: 8px 0; }
details > summary { cursor: pointer; font-size: 0.95rem; }
details[open] > summary { margin-bottom: 6px; }
h3 .cv-age { vertical-align: middle; }
.lookup-bar { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }
.lookup-bar input, .lookup-bar select { font: inherit; font-size: 0.95rem; padding: 8px 10px; background: var(--slot); color: var(--ink);
  border: 2px solid var(--slot-border); min-width: 0; }
.lookup-bar input { flex: 1 1 220px; }
.lookup-bar select { flex: 0 1 160px; }
#lookup-status { font-size: 0.85rem; color: var(--ink-faint); margin: 4px 0 8px; }
.panel { min-width: 0; }
.panel code, .panel h2, .panel h3 { overflow-wrap: anywhere; }
.tree { max-width: 100%; box-sizing: border-box; font-family: "Space Mono", monospace; font-size: 0.8rem; background: var(--slot); border: 2px solid var(--slot-border); padding: 10px 12px;
  overflow-x: auto; white-space: pre; line-height: 1.45; }
"""

SCRIPT = """<script>
(function () {
  var R = %(recipes)s;
  function slot(label) { var d = document.createElement("div"); d.className = "cslot" + (label ? "" : " empty"); if (label) d.textContent = label; return d; }
  document.querySelectorAll("[data-recipes]").forEach(function (host) {
    (R[host.getAttribute("data-recipes")] || []).forEach(function (r) {
      var card = document.createElement("div"); card.className = "recipe";
      var nm = document.createElement("div"); nm.className = "rname"; nm.textContent = r.name; card.appendChild(nm);
      var craft = document.createElement("div"); craft.className = "craft";
      var g = document.createElement("div"); g.className = "cgrid";
      for (var i = 0; i < 9; i++) g.appendChild(slot(r.grid[i] || null));
      craft.appendChild(g);
      var ar = document.createElement("span"); ar.className = "carrow"; ar.textContent = "\\u2192"; craft.appendChild(ar);
      var o = document.createElement("div"); o.className = "cout"; o.textContent = r.out; craft.appendChild(o);
      card.appendChild(craft);
      if (r.note) { var n = document.createElement("div"); n.className = "rnote"; n.textContent = r.note; card.appendChild(n); }
      host.appendChild(card);
    });
  });

  var STORAGE_KEY = "mc-guide-%(name)s-progress-fallback";
  var state = {};
  try { state = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"); } catch (e) { state = {}; }
  function save() { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (e) {} }
  function render() {
    var items = document.querySelectorAll("ul.tasks li[data-id]"), done = 0;
    items.forEach(function (li) {
      var on = !!state[li.getAttribute("data-id")];
      li.classList.toggle("done", on);
      li.setAttribute("aria-checked", on ? "true" : "false");
      li.querySelector(".checkbox").textContent = on ? "\\u2713" : "";
      if (on) done++;
    });
    var pct = items.length ? Math.round(done / items.length * 100) : 0;
    var fill = document.getElementById("progress-fill"), label = document.getElementById("progress-label");
    if (fill) fill.style.width = pct + "%%";
    if (label) label.textContent = done + " / " + items.length + " checked";
  }
  function toggle(id) { state[id] = !state[id]; save(); render(); }
  document.querySelectorAll("ul.tasks li[data-id]").forEach(function (li) {
    li.setAttribute("tabindex", "0"); li.setAttribute("role", "checkbox");
    li.addEventListener("click", function () { toggle(li.getAttribute("data-id")); });
    li.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(li.getAttribute("data-id")); } });
  });
  render();
})();
</script>"""

def include(m):
    with open(os.path.join(here, m.group(1)), encoding="utf-8") as f:
        return f.read().strip()


def build(docs, names):
    src = open(os.path.join(docs, "twinportals.html"), encoding="utf-8").read()
    head = src[: src.index("</style>")]
    for name in names:
        body = open(os.path.join(here, name + ".body.html"), encoding="utf-8").read()
        body = re.sub(r"<!--\s*include:\s*(\S+?)\s*-->", include, body)
        m = re.search(r"<!--\s*title:\s*(.+?)\s*-->", body)
        title = m.group(1) if m else name
        rp = os.path.join(here, name + ".recipes.json")
        recipes = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else {}
        page_head = re.sub(r"<title>.*?</title>", "<title>%s</title>" % title, head, count=1)
        css = EXTRA_CSS + (CV_CSS if name.startswith(("cv-", "dev-")) else "")
        out = (page_head + css + "</style>\n</head>\n<body>\n<div class=\"wrap\">\n"
               + body.strip() + "\n</div>\n\n" + SCRIPT % {"recipes": json.dumps(recipes, ensure_ascii=False, indent=2), "name": name}
               + "\n</body>\n</html>\n")
        with open(os.path.join(docs, name + ".html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(out)
        print("wrote", name + ".html", len(out), "bytes")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2:])
