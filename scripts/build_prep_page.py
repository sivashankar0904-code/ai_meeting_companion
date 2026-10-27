"""Build an interview-prep page (static HTML, no external resources) from a JSON file.

    python scripts/build_prep_page.py prep/persistent-systems.json            # writes prep/persistent-systems.html
    python scripts/build_prep_page.py prep/acme.json -o somewhere/acme.html

JSON: {"company", "round", "date", "length", "subtitle", "brief_title", "brief": [..], "group_intros": {group: text},
"questions": [{"group", "q", "say", "pts": [..], "mine", "gap"}]}. Questions are shown in order, grouped by "group".
Keep every answer inside the tools listed in context/skill_set.md. The personal pages in prep/ are git-ignored.
"""
import argparse
import json
import re
from html import escape as e
from pathlib import Path

parser = argparse.ArgumentParser(description="Build an interview-prep HTML page from a JSON file.")
parser.add_argument("data", type=Path)
parser.add_argument("-o", "--out", type=Path)
_args = parser.parse_args()
META = json.loads(_args.data.read_text(encoding="utf-8"))
OUT = _args.out or _args.data.with_suffix(".html")
QUESTIONS = [dict(q, id=f"q{i}") for i, q in enumerate(META["questions"], 1)]

GROUPS = []
for item in QUESTIONS:
    if item["group"] not in GROUPS:
        GROUPS.append(item["group"])


def card(n, it):
    pts = "".join(f"<li>{e(p)}</li>" for p in it["pts"])
    mine = f'<p class="note"><b>Make it yours.</b> {e(it["mine"])}</p>' if it.get("mine") else ""
    gap = f'<p class="gap"><b>Gap from the interview.</b> {e(it["gap"])}</p>' if it.get("gap") else ""
    return f'''<details class="q" id="{it["id"]}" data-text="{e((it["q"] + " " + it["say"] + " " + " ".join(it["pts"])).lower(), quote=True)}">
<summary><span class="num">{n}</span><span class="qt">{e(it["q"])}</span><label class="done" title="Mark as practised"><input type="checkbox" data-id="{it["id"]}"> <span>Practised</span></label></summary>
<div class="body">
<p class="say"><b>Say first</b>{e(it["say"])}</p>
<ul>{pts}</ul>
{mine}{gap}
</div>
</details>'''


sections = []
n = 0
for g in GROUPS:
    cards = []
    for it in QUESTIONS:
        if it["group"] == g:
            n += 1
            cards.append(card(n, it))
    gid = "g-" + g.lower().replace(" ", "-")
    intro = f'<p class="intro">{e(META["group_intros"][g])}</p>' if g in META.get("group_intros", {}) else ""
    sections.append(f'<section id="{gid}"><h2>{e(g)}</h2>{intro}<div class="cards">{"".join(cards)}</div></section>')

toc = "".join(f'<a href="#g-{g.lower().replace(" ", "-")}">{e(g)}</a>' for g in GROUPS)
total = n
CHIPS = ''.join(f'<span class="chip"><b>{e(k)}</b> {e(META[v])}</span>' for k, v in (('Company', 'company'), ('Round', 'round'), ('Date', 'date'), ('Length', 'length')) if META.get(v))
BRIEF = ''.join(f'<li>{e(b)}</li>' for b in META['brief'])
SLUG = re.sub(r'[^a-z0-9]+', '-', META['company'].lower()).strip('-')

HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(META["company"])} interview prep</title>
<style>
:root{{
  --bg:#f6f5f1; --surface:#ffffff; --surface2:#f0eee8; --ink:#1d2420; --muted:#59645d; --line:#dedbd1;
  --accent:#17803d; --accent-ink:#ffffff; --accent-soft:#e3f1e8; --warn:#9a5b06; --warn-soft:#fbefd9;
  color-scheme:light;
}}
@media (prefers-color-scheme:dark){{
  :root{{
    --bg:#121512; --surface:#1a1f1b; --surface2:#222923; --ink:#e8eee9; --muted:#9fada4; --line:#2e372f;
    --accent:#47b873; --accent-ink:#08150d; --accent-soft:#16301f; --warn:#f0b25c; --warn-soft:#3a2a12;
    color-scheme:dark;
  }}
}}
*{{box-sizing:border-box}}
html{{scroll-behavior:smooth;scroll-padding-top:16px}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-text-size-adjust:100%}}
:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
h1,h2,p{{margin:0}}
.layout{{display:grid;grid-template-columns:230px minmax(0,1fr);gap:28px;max-width:1100px;margin:0 auto;padding:24px 16px 80px}}
nav.toc{{position:sticky;top:16px;align-self:start;display:flex;flex-direction:column;gap:2px}}
nav.toc h2{{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 8px;font-weight:600}}
nav.toc a{{text-decoration:none;color:var(--ink);padding:7px 10px;border-radius:8px;font-size:14px}}
nav.toc a:hover{{background:var(--surface2)}}
main{{min-width:0}}
header.top h1{{font-size:30px;line-height:1.2;letter-spacing:-.02em}}
header.top p{{color:var(--muted);margin-top:6px}}
.meta{{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}}
.chip{{background:var(--surface);border:1px solid var(--line);border-radius:999px;padding:4px 12px;font-size:13px;color:var(--muted)}}
.chip b{{color:var(--ink);font-weight:600}}
.brief{{margin-top:18px;background:var(--accent-soft);border-radius:12px;padding:14px 18px}}
.brief h2{{font-size:15px;margin-bottom:6px}}
.brief ul{{margin:0;padding-left:20px}}
.tools{{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0 6px;align-items:center}}
.tools input[type=search]{{flex:1 1 220px;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--ink);font:inherit}}
.btn{{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:10px;padding:9px 14px;font:inherit;font-weight:600;cursor:pointer}}
.btn:hover{{background:var(--surface2)}}
.progress{{font-size:14px;color:var(--muted)}}
.bar{{height:6px;background:var(--surface2);border-radius:3px;overflow:hidden;margin:8px 0 4px}}
.bar i{{display:block;height:100%;background:var(--accent);width:0;transition:width .2s}}
section{{margin-top:36px}}
section>h2{{font-size:22px;letter-spacing:-.01em;padding-bottom:8px;border-bottom:1px solid var(--line);margin-bottom:14px}}
.intro{{color:var(--muted);margin-bottom:12px}}
.cards{{display:grid;gap:10px}}
details.q{{background:var(--surface);border:1px solid var(--line);border-radius:12px}}
details.q[open]{{border-color:var(--accent)}}
summary{{list-style:none;cursor:pointer;display:grid;grid-template-columns:30px minmax(0,1fr) auto;gap:12px;align-items:start;padding:14px 16px}}
summary::-webkit-details-marker{{display:none}}
.num{{width:28px;height:28px;border-radius:50%;background:var(--accent);color:var(--accent-ink);display:grid;place-items:center;font-weight:700;font-size:13px}}
.qt{{font-weight:600}}
.done{{font-size:13px;color:var(--muted);display:flex;gap:6px;align-items:center;white-space:nowrap}}
.body{{padding:0 16px 16px 58px}}
.say{{background:var(--surface2);border-radius:10px;padding:10px 14px;margin-bottom:10px}}
.say b{{display:block;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:600;margin-bottom:2px}}
.body ul{{margin:0 0 10px;padding-left:20px;display:grid;gap:4px}}
.note,.gap{{border-radius:10px;padding:10px 14px;margin-top:8px;font-size:15px}}
.note{{background:var(--accent-soft)}}
.gap{{background:var(--warn-soft);color:var(--ink)}}
.gap b{{color:var(--warn)}}
.hidden{{display:none}}
.empty{{display:none;color:var(--muted);margin-top:20px}}
@media (max-width:820px){{
  .layout{{grid-template-columns:minmax(0,1fr)}}
  nav.toc{{position:static;flex-direction:row;flex-wrap:wrap;gap:6px}}
  nav.toc h2{{width:100%}}
  nav.toc a{{background:var(--surface);border:1px solid var(--line)}}
  summary{{grid-template-columns:30px minmax(0,1fr)}}
  .done{{grid-column:2}}
  .body{{padding-left:16px}}
}}
</style>
</head>
<body>
<div class="layout">
<nav class="toc" aria-label="Sections"><h2>Sections</h2>{toc}</nav>
<main>
<header class="top">
<h1>{e(META["company"])}: interview prep</h1>
<p>{e(META["subtitle"])}</p>
<div class="meta">{CHIPS}</div>
<div class="brief">
<h2>{e(META["brief_title"])}</h2>
<ul>{BRIEF}</ul>
</div>
</header>
<div class="tools">
<input type="search" id="q" placeholder="Search questions and answers" aria-label="Search">
<button class="btn" id="expand" type="button">Expand all</button>
<button class="btn" id="collapse" type="button">Collapse all</button>
</div>
<div class="progress"><span id="count">0</span> of {total} practised</div>
<div class="bar"><i id="fill"></i></div>
{"".join(sections)}
<p class="empty" id="empty">No question matches your search.</p>
</main>
</div>
<script>
(function(){{
  var KEY='{SLUG}-prep-v1', done={{}};
  try{{ done=JSON.parse(localStorage.getItem(KEY)||'{{}}'); }}catch(e){{ done={{}}; }}
  var boxes=[].slice.call(document.querySelectorAll('input[type=checkbox][data-id]'));
  var qs=[].slice.call(document.querySelectorAll('details.q'));
  function save(){{ try{{ localStorage.setItem(KEY, JSON.stringify(done)); }}catch(e){{}} }}
  function update(){{
    var n=boxes.filter(function(b){{return b.checked;}}).length;
    document.getElementById('count').textContent=n;
    document.getElementById('fill').style.width=(100*n/boxes.length)+'%';
  }}
  boxes.forEach(function(b){{
    b.checked=!!done[b.dataset.id];
    b.addEventListener('click',function(ev){{ev.stopPropagation();}});
    b.addEventListener('change',function(){{ done[b.dataset.id]=b.checked; save(); update(); }});
  }});
  document.querySelectorAll('.done').forEach(function(l){{ l.addEventListener('click',function(ev){{ev.stopPropagation();}}); }});
  document.getElementById('expand').onclick=function(){{ qs.forEach(function(d){{ if(!d.classList.contains('hidden')) d.open=true; }}); }};
  document.getElementById('collapse').onclick=function(){{ qs.forEach(function(d){{ d.open=false; }}); }};
  document.getElementById('q').addEventListener('input',function(){{
    var t=this.value.trim().toLowerCase(), shown=0;
    qs.forEach(function(d){{
      var hit=!t||d.dataset.text.indexOf(t)>-1;
      d.classList.toggle('hidden',!hit); if(hit) shown++;
    }});
    document.querySelectorAll('section').forEach(function(s){{
      s.classList.toggle('hidden',!s.querySelector('details.q:not(.hidden)'));
    }});
    document.getElementById('empty').style.display=shown?'none':'block';
  }});
  update();
}})();
</script>
</body>
</html>
'''
OUT.write_text(HTML, encoding="utf-8")
print("wrote", OUT, len(HTML), "bytes,", total, "questions")
