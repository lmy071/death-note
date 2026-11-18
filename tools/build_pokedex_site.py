#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据抓取结果生成可离线浏览的 HTML 站点：index.html + pages/*.html。"""
import argparse
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pokedex_naming import image_file  # noqa: E402


def natural_key(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]

CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { margin:0; font-family:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
       background:#f5f6f8; color:#222; }
a { color:inherit; }
header { position:sticky; top:0; z-index:5; background:#fff; padding:14px 20px;
         box-shadow:0 2px 10px rgba(0,0,0,.08); }
h1 { font-size:18px; margin:0 0 10px; }
h1 small { font-weight:400; color:#888; font-size:12px; margin-left:8px; }
#q { width:100%; max-width:420px; padding:9px 12px; border:1px solid #ccd; border-radius:8px; font-size:14px; }
#types { margin-top:10px; display:flex; flex-wrap:wrap; gap:6px; }
#types button { border:1px solid #ccd; background:#fff; border-radius:999px; padding:4px 12px; font-size:12px; cursor:pointer; }
#types button.on { background:#3b6cf0; color:#fff; border-color:#3b6cf0; }
#count { margin-top:8px; font-size:12px; color:#777; }
main { display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:14px; padding:20px; }
.card { background:#fff; border-radius:14px; padding:12px; text-decoration:none; display:flex;
        flex-direction:column; align-items:center; gap:6px; box-shadow:0 1px 4px rgba(0,0,0,.08);
        transition:transform .12s, box-shadow .12s; }
.card:hover { transform:translateY(-3px); box-shadow:0 6px 18px rgba(0,0,0,.14); }
.card img { width:100%; aspect-ratio:1; object-fit:contain; background:#fafbfc; border-radius:10px; }
.no { font-size:11px; color:#999; align-self:flex-start; }
.name { font-size:14px; font-weight:600; text-align:center; }
.types { display:flex; gap:4px; flex-wrap:wrap; justify-content:center; }
.t { font-size:11px; padding:1px 8px; border-radius:999px; background:#e8ecf5; }
.hidden { display:none; }
footer { padding:20px; font-size:12px; color:#888; text-align:center; }
/* detail */
.detail { max-width:960px; margin:0 auto; padding:24px 20px 60px; }
.back { display:inline-block; margin-bottom:16px; font-size:13px; color:#3b6cf0; text-decoration:none; }
.hero { display:flex; gap:26px; background:#fff; border-radius:18px; padding:24px;
        box-shadow:0 2px 10px rgba(0,0,0,.08); flex-wrap:wrap; }
.hero img { width:260px; max-width:100%; aspect-ratio:1; object-fit:contain; background:#fafbfc; border-radius:14px; }
.hero h2 { margin:0 0 4px; font-size:26px; }
.hero .sub { color:#888; font-size:13px; margin-bottom:14px; }
.kv { display:grid; grid-template-columns:auto 1fr; gap:6px 14px; font-size:14px; margin:0; }
.kv dt { color:#777; }
.kv dd { margin:0; }
section.block { background:#fff; border-radius:18px; padding:20px 24px; margin-top:18px;
                box-shadow:0 2px 10px rgba(0,0,0,.08); }
section.block h3 { margin:0 0 12px; font-size:16px; }
ul.clean { margin:0; padding-left:18px; font-size:14px; line-height:1.75; }
ul.clean li span.desc { color:#666; }
.bars { display:grid; gap:6px; font-size:13px; }
.bar { display:grid; grid-template-columns:52px 1fr 32px; align-items:center; gap:10px; }
.bar .track { height:10px; background:#eef1f6; border-radius:6px; overflow:hidden; }
.bar .fill { height:100%; background:#3b6cf0; border-radius:6px; }
.forms { display:flex; gap:12px; flex-wrap:wrap; }
.form-card { width:132px; text-align:center; text-decoration:none; font-size:12px; }
.form-card img { width:100%; aspect-ratio:1; object-fit:contain; background:#fafbfc; border-radius:10px; }
.evo { display:flex; align-items:center; gap:10px; flex-wrap:wrap; font-size:13px; margin-bottom:8px; }
.evo .arrow { color:#aaa; }
.src { font-size:12px; color:#888; margin-top:18px; word-break:break-all; }
@media (prefers-color-scheme: dark) {
  body { background:#14161a; color:#e6e8ee; }
  header, .hero, section.block { background:#1c1f26; }
  .card { background:#1c1f26; }
  .card img, .hero img, .form-card img { background:#22252c; }
  #q, #types button { background:#22252c; color:#e6e8ee; border-color:#333a44; }
  .t { background:#2a2f38; }
  .bar .track { background:#2a2f38; }
  ul.clean li span.desc { color:#a8b0bd; }
}
"""

def esc(s):
    return html.escape(s or "")

def types_html(types, cls="t"):
    return "".join(f'<span class="{cls}">{esc(t)}</span>' for t in types)

def render_detail(r, records_by_id, images_dir):
    title = r.get("name", "")
    if r.get("form_name"):
        title += f"（{r['form_name']}）"
    img = r.get("image_file", "").replace("../images/", "../images/")

    def has_img(eid):
        rec = records_by_id.get(eid)
        if not rec:
            return False
        name = os.path.basename(rec.get("image_file", ""))
        return bool(name) and os.path.exists(os.path.join(images_dir, name))

    def img_src(eid):
        rec = records_by_id.get(eid) or {}
        return os.path.basename(rec.get("image_file", ""))

    kv = []
    kv.append(("图鉴编号", f"No.{esc(r.get('dex_no',''))}"))
    if r.get("form_name"):
        kv.append(("样子", esc(r["form_name"])))
    if r.get("category"):
        kv.append(("分类", esc(r["category"])))
    if r.get("height"):
        kv.append(("身高", esc(r["height"])))
    if r.get("weight"):
        kv.append(("体重", esc(r["weight"])))
    if r.get("gender"):
        kv.append(("性别", esc(r["gender"])))
    kv_html = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in kv)

    ab = "".join(
        f"<li><b>{esc(a['name'])}</b><br><span class='desc'>{esc(a['description'])}</span></li>"
        for a in r.get("abilities", []))

    stats = r.get("stat_bars") or {}
    mx = max(stats.values()) if stats else 15
    bars = "".join(
        f'<div class="bar"><div>{esc(k)}</div><div class="track">'
        f'<div class="fill" style="width:{int(v / (mx or 1) * 100)}%"></div></div>'
        f'<div>{v}</div></div>' for k, v in stats.items())

    entries = "".join(f"<li>{esc(s)}</li>" for s in r.get("dex_entries", []))

    forms = ""
    if r.get("forms"):
        items = []
        for f in r["forms"]:
            src = f"../images/{img_src(f['id'])}" if has_img(f["id"]) else ""
            thumb = (f'<img loading="lazy" src="{esc(src)}" alt="{esc(f["name"])}">'
                     if src else '<div style="aspect-ratio:1;background:#fafbfc;border-radius:10px"></div>')
            inner = (f'{thumb}<div>{esc(f["name"])}</div>'
                     f'<div style="color:#999">{esc(f.get("form_name",""))}</div>'
                     f'<div class="types">{types_html(f.get("types", []))}</div>')
            if f["id"] in records_by_id:
                items.append(f'<a class="form-card" href="{esc(f["id"])}.html">{inner}</a>')
            else:
                items.append(f'<div class="form-card">{inner}</div>')
        forms = f'<section class="block"><h3>样子</h3><div class="forms">{"".join(items)}</div></section>'

    evo = ""
    if r.get("evolutions"):
        rows = []
        for chain in r["evolutions"]:
            parts = []
            for i, s in enumerate(chain):
                nm = s["name"] + (f"（{s['form_name']}）" if s.get("form_name") else "")
                label = f'{esc(s["dex_no"])} {esc(nm)}'
                if s["id"] in records_by_id:
                    parts.append(f'<a href="{esc(s["id"])}.html">{label}</a>')
                else:
                    parts.append(f"<span>{label}</span>")
                if i < len(chain) - 1:
                    parts.append('<span class="arrow">→</span>')
            rows.append('<div class="evo">' + "".join(parts) + "</div>")
        evo = f'<section class="block"><h3>进化</h3>{"".join(rows)}</section>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(r.get('dex_no',''))} {esc(title)} · 宝可梦图鉴</title>
<style>{CSS}</style></head><body>
<div class="detail">
  <a class="back" href="../index.html">← 返回图鉴列表</a>
  <div class="hero">
    <img src="{esc(img)}" alt="{esc(title)}">
    <div style="flex:1; min-width:260px">
      <h2>{esc(r.get('dex_no',''))} {esc(title)}</h2>
      <div class="sub">属性：{types_html(r.get('types', []))}</div>
      <dl class="kv">{kv_html}</dl>
    </div>
  </div>
  <section class="block"><h3>特性</h3><ul class="clean">{ab}</ul></section>
  <section class="block"><h3>图鉴说明</h3><ul class="clean">{entries}</ul></section>
  <section class="block"><h3>能力（官网刻度，非实际数值）</h3><div class="bars">{bars}</div></section>
  {forms}
  {evo}
  <section class="block"><h3>弱点</h3><div class="types">{types_html(r.get('weaknesses', []))}</div></section>
  <div class="src">来源：{esc(r.get('source',''))}　抓取时间：{esc(r.get('fetched_at',''))}</div>
</div>
</body></html>
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    args = ap.parse_args()
    root = os.path.abspath(args.dir)

    records = []
    for fn in sorted(os.listdir(os.path.join(root, "data"))):
        if fn.endswith(".json"):
            with open(os.path.join(root, "data", fn), encoding="utf-8") as f:
                records.append(json.load(f))
    records.sort(key=lambda r: natural_key(r.get("id", "")))
    by_id = {r["id"]: r for r in records}

    pages_dir = os.path.join(root, "pages")
    os.makedirs(pages_dir, exist_ok=True)
    for r in records:
        with open(os.path.join(pages_dir, f"{r['id']}.html"), "w", encoding="utf-8") as f:
            f.write(render_detail(r, by_id, os.path.join(root, "images")))

    cards = []
    for r in records:
        title = r.get("name", "")
        if r.get("form_name"):
            title += f"（{r['form_name']}）"
        img = r.get("image_file", "").replace("../images/", "images/")
        search = " ".join([r.get("dex_no", ""), r.get("id", ""), title, " ".join(r.get("types", []))])
        cards.append(
            f'<a class="card" href="pages/{r["id"]}.html" data-search="{esc(search)}" '
            f'data-types="{esc("|".join(r.get("types", [])))}">'
            f'<div class="no">No.{esc(r.get("dex_no",""))}</div>'
            f'<img loading="lazy" src="{esc(img)}" alt="{esc(title)}">'
            f'<div class="name">{esc(title)}</div>'
            f'<div class="types">{types_html(r.get("types", []))}</div></a>')

    all_types = sorted({t for r in records for t in r.get("types", [])})
    type_buttons = "".join(f'<button data-t="{esc(t)}">{esc(t)}</button>' for t in all_types)

    page = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>宝可梦官方图鉴离线存档</title>
<style>{CSS}</style></head><body>
<header>
  <h1>宝可梦官方图鉴离线存档<small>数据来源：pokemon.cn 官方中文图鉴</small></h1>
  <input id="q" type="search" placeholder="搜索名称 / 编号 / 属性…">
  <div id="types">{type_buttons}</div>
  <div id="count"></div>
</header>
<main id="grid">
{"".join(cards)}
</main>
<footer>共 {len(records)} 个条目 · 图片与文字版权归 The Pokémon Company 所有，仅供个人离线查阅</footer>
<script>
const cards = [...document.querySelectorAll('.card')];
const q = document.getElementById('q');
const count = document.getElementById('count');
const active = new Set();
function apply() {{
  const term = q.value.trim().toLowerCase();
  let n = 0;
  for (const c of cards) {{
    const okTerm = !term || c.dataset.search.toLowerCase().includes(term);
    const ctypes = c.dataset.types ? c.dataset.types.split('|') : [];
    const okType = active.size === 0 || [...active].every(t => ctypes.includes(t));
    const show = okTerm && okType;
    c.classList.toggle('hidden', !show);
    if (show) n++;
  }}
  count.textContent = `显示 ${{n}} / ${{cards.length}} 个条目`;
}}
q.addEventListener('input', apply);
document.querySelectorAll('#types button').forEach(b => b.addEventListener('click', () => {{
  const t = b.dataset.t;
  if (active.has(t)) {{ active.delete(t); b.classList.remove('on'); }}
  else {{ active.add(t); b.classList.add('on'); }}
  apply();
}}));
apply();
</script>
</body></html>
"""
    with open(os.path.join(root, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print(f"index.html + {len(records)} pages written")

if __name__ == "__main__":
    main()
