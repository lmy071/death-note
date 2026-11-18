#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取宝可梦官网中文图鉴（https://www.pokemon.cn/play/pokedex/）全部条目。

用法:
    python tools/scrape_pokedex.py --out pokemon-pokedex --delay 0.3
"""
import argparse
import gzip
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque

from lxml import html as LH

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pokedex_naming import image_stem  # noqa: E402

BASE = "https://www.pokemon.cn/play/pokedex/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
ENTRY_RE = re.compile(r"/play/pokedex/(\d{4}(?:_\d+)?)")


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def text_of(el):
    return "" if el is None else norm("".join(el.itertext()))


def first(scope, expr):
    if scope is None:
        return None
    hits = scope.xpath(expr)
    return hits[0] if hits else None


def fetch(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Accept-Encoding": "gzip",
                "Referer": BASE,
            })
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return r.geturl(), raw
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, None
            last = e
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(1.0 + i * 1.5)
    raise RuntimeError(f"fetch failed: {url} ({last})")


def save_image(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 1024:
        return True
    if not url:
        return False
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if r.status == 200 and data[:4] == b"\x89PNG":
                with open(path, "wb") as f:
                    f.write(data)
                return True
        except Exception:
            time.sleep(1 + i)
    return False


def types_in(scope):
    out = []
    for el in (scope.xpath('.//*[contains(@class,"pokemon-type__type") '
                           'and not(contains(@class,"pokemon-type__title"))]')
               if scope is not None else []):
        t = text_of(el)
        if t and t not in out:
            out.append(t)
    return out


def parse(entry_id, page_url, root):
    body = first(root, "body")
    res = {"id": entry_id, "source": page_url,
           "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

    contents = body.xpath('//div[contains(@class,"pokemon-detail-contents")]')
    if contents:
        res["dex_no"] = contents[0].get("data-zukanid")
        res["sub_id"] = contents[0].get("data-zukansubid")
        res["max_status"] = contents[0].get("data-max-status")

    res["name"] = text_of(first(body, './/p[contains(@class,"pokemon-slider__main-name")]'))
    res["form_name"] = text_of(first(body, './/p[contains(@class,"pokemon-slider__main-subname")]'))
    res["dex_no_display"] = text_of(first(body, './/p[contains(@class,"pokemon-slider__main-no")]'))

    img = first(body, './/img[contains(@class,"pokemon-img__front")]')
    res["image_url"] = img.get("src") if img is not None else ""

    res["types"] = types_in(first(body, './/div[@class="pokemon-type"]'))

    weak = first(body, './/div[contains(@class,"pokemon-weakness__items")]')
    res["weaknesses"] = [text_of(e) for e in weak.xpath(".//span") if text_of(e)] if weak is not None else []

    info = first(body, './/div[@class="pokemon-info"]')
    if info is not None:
        def val(cls):
            return text_of(first(info, f'.//div[@class="{cls}"]/span[contains(@class,"pokemon-info__value")]'))

        res["height"] = val("pokemon-info__height")
        res["weight"] = val("pokemon-info__weight")
        res["category"] = val("pokemon-info__category")

        g = first(info, './/div[@class="pokemon-info__gender"]/span[contains(@class,"pokemon-info__value")]')
        icons = [i.get("src", "") for i in g.iter("img")] if g is not None else []
        male = any("icon_male" in s for s in icons)
        female = any("icon_female" in s for s in icons)
        res["gender"] = "♂/♀" if male and female else "♂" if male else "♀" if female else "无性别"

        abilities = []
        ab_box = first(info, './/div[@class="pokemon-info__abilities"]')
        if ab_box is not None:
            for sp in ab_box.xpath('.//span[contains(@class,"pokemon-info__value") '
                                   'and not(contains(@class,"pokemon-info__value--title")) '
                                   'and not(contains(@class,"pokemon-info__value--body"))]'):
                n = text_of(sp)
                if n:
                    abilities.append({"name": n, "description": ""})
        descs = {}
        for blk in info.xpath('.//div[@class="pokemon-info__ability_info"]'):
            t = text_of(first(blk, './/span[contains(@class,"pokemon-info__value--title")]'))
            b = text_of(first(blk, './/span[contains(@class,"pokemon-info__value--body")]'))
            if t:
                descs[t] = b
        for a in abilities:
            a["description"] = descs.get(a["name"], "")
        res["abilities"] = abilities

    stories = body.xpath('//div[contains(@class,"pokemon-story")]//p[contains(@class,"pokemon-story__body")]')
    res["dex_entries"] = [text_of(p) for p in stories if text_of(p)]

    stats = {}
    for blk in body.xpath('//div[@class="pokemon-status"]'):
        label = text_of(first(blk, './/div[contains(@class,"pokemon-status__title")]'))
        if not label:
            continue
        lv = 0
        for sp in blk.xpath('.//span[contains(@class,"pokemon-status__scale")]'):
            m = re.search(r"\bd(\d+)\b", sp.get("class", ""))
            if m:
                lv = max(lv, int(m.group(1)))
        stats[label] = lv
    res["stat_bars"] = stats

    forms = []
    for a in body.xpath('//div[contains(@class,"pokemon-style__boxes")]//a'):
        m = ENTRY_RE.search(a.get("href", ""))
        img_el = first(a, ".//img")
        forms.append({
            "id": m.group(1) if m else "",
            "name": text_of(first(a, './/span[contains(@class,"pokemon-style-box__name")]')),
            "form_name": text_of(first(a, './/span[contains(@class,"pokemon-style-box__subname")]')),
            "types": [text_of(s) for s in a.xpath('.//div[contains(@class,"pokemon-style-box__type")]//span')
                      if text_of(s)],
            "image_url": img_el.get("src", "") if img_el is not None else "",
        })
    res["forms"] = [f for f in forms if f["name"]]

    evo_chains = []
    for chain in body.xpath('//div[contains(@class,"pokemon-evolution ")]'):
        steps = []
        for a in chain.xpath('.//div[contains(@class,"pokemon-evolution-itembox")]//a'):
            m = ENTRY_RE.search(a.get("href", ""))
            steps.append({
                "id": m.group(1) if m else "",
                "dex_no": text_of(first(a, './/p[contains(@class,"pokemon-evolution-box__no")]')),
                "name": text_of(first(a, './/p[contains(@class,"pokemon-evolution-item__info-name")]')),
                "form_name": text_of(first(a, './/p[contains(@class,"pokemon-evolution-item__info-subname")]')),
                "types": [text_of(s) for s in a.xpath('.//div[contains(@class,"pokemon-evolution-item__info-type")]//span')
                          if text_of(s)],
            })
        if steps:
            evo_chains.append(steps)
    res["evolutions"] = evo_chains

    links = set()
    for a in body.iter("a"):
        m = ENTRY_RE.search(a.get("href") or "")
        if m:
            links.add(m.group(1))
    res["links"] = sorted(links)
    return res


def to_markdown(d):
    L = []
    title = d.get("name", "")
    if d.get("form_name"):
        title = f"{title}（{d['form_name']}）"
    L.append(f"# {d.get('dex_no', '')} {title}\n")
    L.append(f"- 图鉴编号：No.{d.get('dex_no', '')}"
             + (f"（样子 {d.get('sub_id')}）" if d.get("sub_id") not in (None, "", "0") else ""))
    if d.get("types"):
        L.append(f"- 属性：{' / '.join(d['types'])}")
    if d.get("weaknesses"):
        L.append(f"- 弱点：{' / '.join(d['weaknesses'])}")
    for key, label in (("height", "身高"), ("weight", "体重"), ("category", "分类"), ("gender", "性别")):
        if d.get(key):
            L.append(f"- {label}：{d[key]}")
    if d.get("abilities"):
        L.append("- 特性：")
        for a in d["abilities"]:
            L.append(f"  - {a['name']}：{a['description']}")
    if d.get("stat_bars"):
        L.append("- 能力条（官网 15 级刻度）：")
        L.append("  " + " / ".join(f"{k} {v}" for k, v in d["stat_bars"].items()))
    if d.get("dex_entries"):
        L.append("\n## 图鉴说明")
        for i, s in enumerate(d["dex_entries"], 1):
            L.append(f"{i}. {s}")
    if d.get("forms"):
        L.append("\n## 样子")
        for f in d["forms"]:
            extra = f"（{f['form_name']}）" if f.get("form_name") else ""
            L.append(f"- {f['id']} {f['name']}{extra} {' / '.join(f['types'])}")
    if d.get("evolutions"):
        L.append("\n## 进化")
        for chain in d["evolutions"]:
            L.append("- " + " → ".join(
                f"{s['dex_no']} {s['name']}" + (f"（{s['form_name']}）" if s.get("form_name") else "")
                for s in chain))
    if d.get("image_file"):
        L.append(f"\n![{title}]({d['image_file']})")
    L.append(f"\n来源：{d.get('source', '')}")
    return "\n".join(L) + "\n"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--delay", type=float, default=0.5)
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-images", action="store_true")
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    dirs = {k: os.path.join(out, k) for k in ("data", "markdown", "images", "raw_html")}
    for p in dirs.values():
        os.makedirs(p, exist_ok=True)

    queue = deque(args.ids if args.ids else [f"{i:04d}" for i in range(1, 1026)])
    seen, failed, done = set(), [], 0
    stats = {"pages": 0, "images": 0, "skipped": 0}

    while queue:
        eid = queue.popleft()
        if eid in seen:
            continue
        seen.add(eid)
        if args.limit and done >= args.limit:
            break

        json_path = os.path.join(dirs["data"], f"{eid}.json")
        if os.path.exists(json_path):
            stats["skipped"] += 1
            try:
                with open(json_path, encoding="utf-8") as f:
                    prev = json.load(f)
                for l in prev.get("links", []):
                    if l not in seen:
                        queue.append(l)
            except Exception:
                pass
            continue

        try:
            final_url, raw = fetch(BASE + eid + "/")
        except RuntimeError as e:
            failed.append({"id": eid, "error": str(e)})
            print(f"[FAIL] {eid} {e}", flush=True)
            continue

        if raw is None:
            failed.append({"id": eid, "error": "404"})
            print(f"[404 ] {eid}", flush=True)
            time.sleep(args.delay)
            continue

        with open(os.path.join(dirs["raw_html"], f"{eid}.html"), "wb") as f:
            f.write(raw)

        rec = parse(eid, final_url, LH.fromstring(raw))

        if rec.get("image_url") and not args.no_images:
            ext = os.path.splitext(urllib.parse.urlparse(rec["image_url"]).path)[1] or ".png"
            fname = image_stem(rec) + ext
            if save_image(rec["image_url"], os.path.join(dirs["images"], fname)):
                rec["image_file"] = f"../images/{fname}"
                stats["images"] += 1

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
        with open(os.path.join(dirs["markdown"], f"{eid}.md"), "w", encoding="utf-8") as f:
            f.write(to_markdown(rec))

        for l in rec.get("links", []):
            if l not in seen:
                queue.append(l)

        done += 1
        stats["pages"] += 1
        print(f"[{stats['pages']:5d}] {eid} {rec.get('name','')} {rec.get('form_name','')} "
              f"| queue={len(queue)}", flush=True)
        time.sleep(args.delay)

    summary = {
        "source": BASE,
        "crawled_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "pages": stats["pages"],
        "skipped_existing": stats["skipped"],
        "images": stats["images"],
        "failed": failed,
    }
    os.makedirs(os.path.join(out, "_meta"), exist_ok=True)
    with open(os.path.join(out, "_meta", "crawl_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
