#!/usr/bin/env python3
"""下载崩坏3圣痕立绘原图；支持重试、断点续传及按像素去重。

依赖 Pillow。示例：python3 download.py
"""

import argparse
import csv
import hashlib
import html
import io
import json
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import unquote, urlencode
from urllib.request import Request, urlopen

from PIL import Image


ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
OFFICIAL = "https://act-api-takumi-static.mihoyo.com/common/blackboard/bh3_wiki"
BWIKI = "https://wiki.biligame.com/bh3/api.php"
FANDOM = "https://honkaiimpact3.fandom.com/api.php"
HEADERS = {"User-Agent": "BH3StigmataImageArchive/1.0 (personal collection)"}


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def request(url):
    for attempt in range(5):
        try:
            with urlopen(Request(url, headers=HEADERS), timeout=45) as response:
                return response.read()
        except Exception as exc:
            if isinstance(exc, HTTPError) and exc.code in (400, 401, 403, 404):
                raise
            if attempt == 4:
                raise
            wait = min(2 ** (attempt + 1), 30)
            if isinstance(exc, HTTPError):
                retry_after = exc.headers.get("Retry-After", "")
                if retry_after.isdigit():
                    wait = min(max(wait, int(retry_after)), 45)
            time.sleep(wait)


def api(base, **params):
    url = base + "?" + urlencode(params)
    result = json.loads(request(url))
    if "error" in result or result.get("retcode", 0) != 0:
        raise RuntimeError(f"API error: {result}")
    return result


def parallel(items, function, workers, label):
    output, failures = [], []
    total = len(items)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(function, item): item for item in items}
        for n, future in enumerate(as_completed(futures), 1):
            item = futures[future]
            try:
                output.append(future.result())
            except Exception as exc:
                failures.append({"item": item, "error": str(exc)})
                print(f"{label} ERROR {str(item)[:100]}: {exc}", flush=True)
            if n % 50 == 0 or n == total:
                print(f"{label}: {n}/{total}, failed={len(failures)}", flush=True)
    return output, failures


def official_images(workers, refresh):
    data = api(OFFICIAL + "/v1/home/content/list", app_sn="bh3_wiki", channel_id=19)
    write_json(ROOT / "metadata" / "official_catalog.json", data)
    entries = data["data"]["list"][0]["list"]
    print(f"米游社官方圣痕目录: {len(entries)} 件", flush=True)

    def detail(entry):
        content_id = entry["content_id"]
        path = CACHE / "details" / f"{content_id}.json"
        if path.exists() and not refresh:
            return read_json(path)
        content = api(OFFICIAL + "/v1/content/info", app_sn="bh3_wiki", content_id=content_id)["data"]["content"]
        urls = []
        for section in content.get("contents", []):
            for encoded in re.findall(r'data-data="([^"]+)"', section.get("text", "")):
                parts = json.loads(unquote(html.unescape(encoded)))
                for part in parts:
                    if part.get("tmplKey") == "stigmata" and part.get("partKey") == "main":
                        avatar = part.get("data", {}).get("avatar", "")
                        if avatar and avatar not in urls:
                            urls.append(avatar)
        if not urls:
            raise ValueError(f"没有找到圣痕立绘: {entry['title']}")
        records = [{
            "source": "米游社官方档案馆", "title": entry["title"], "content_id": content_id,
            "url": url, "page": f"https://bbs.mihoyo.com/bh3/wiki/content/{content_id}/detail",
            "folder": "", "variant": i + 1, "updated_at": content.get("mtime", ""),
        } for i, url in enumerate(urls)]
        write_json(path, records)
        return records

    groups, failures = parallel(entries, detail, workers, "官方详情")
    return sorted([r for group in groups for r in group], key=lambda r: (r["title"], r["variant"])), failures


def wiki_images(base, titles, source, folder, workers):
    batches = [titles[i:i + 50] for i in range(0, len(titles), 50)]

    def batch(names):
        data = api(base, action="query", prop="imageinfo", iiprop="url|size|sha1", titles="|".join(names), format="json")
        return list(data["query"]["pages"].values())

    groups, failures = parallel(batches, batch, min(workers, 3), source + "文件信息")
    records = []
    for page in [p for group in groups for p in group]:
        info = page.get("imageinfo", [])
        if not info:
            failures.append({"item": page["title"], "error": "来源目录引用了不存在的图片文件"})
            continue
        info = info[0]
        image_url = info["url"]
        # Fandom CDN 默认会返回有损 WebP；明确请求原文件以匹配 SHA1。
        if source == "Honkai Impact 3 Wiki":
            image_url += ("&" if "?" in image_url else "?") + "format=original"
        records.append({
            "source": source, "title": page["title"].split(":", 1)[1].rsplit(".", 1)[0],
            "url": image_url, "page": info["descriptionurl"], "folder": folder,
            "expected_width": info["width"], "expected_height": info["height"],
            "expected_bytes": info["size"], "expected_sha1": info["sha1"],
        })
    return sorted(records, key=lambda r: r["title"]), failures


def supplemental_images(workers):
    bwiki = api(BWIKI, action="parse", page="圣痕图鉴", prop="images", format="json")
    titles = ["File:" + name for name in bwiki["parse"]["images"]]
    bwiki_records, failures = wiki_images(BWIKI, titles, "BWIKI", "补充立绘/BWIKI", workers)
    members, continuation = [], {}
    while True:
        result = api(FANDOM, action="query", list="categorymembers", cmtitle="Category:Stigmata_Figures", cmtype="file", cmlimit=500, format="json", **continuation)
        members.extend(result["query"]["categorymembers"])
        continuation = result.get("continue")
        if not continuation:
            break
    fandom_records, more_failures = wiki_images(FANDOM, [m["title"] for m in members], "Honkai Impact 3 Wiki", "补充立绘/国际服及历史版本", workers)
    print(f"补充来源: BWIKI {len(titles)} 个引用，国际服 Wiki {len(members)} 个文件", flush=True)
    return bwiki_records + fandom_records, failures + more_failures


def inspect_image(data):
    with Image.open(io.BytesIO(data)) as image:
        image.verify()
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        extension = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp", "GIF": ".gif"}.get(image.format)
        if not extension:
            raise ValueError(f"不支持的图片格式: {image.format}")
        rgba = image.convert("RGBA")
        # 透明像素的 RGB 不影响显示，统一后用于精确去重；保存的原图不作修改。
        rgba.paste((0, 0, 0, 0), mask=rgba.getchannel("A").point(lambda a: 255 if a == 0 else 0))
        pixels = hashlib.sha256(str(image.size).encode() + rgba.tobytes()).hexdigest()
        return {"width": image.width, "height": image.height, "extension": extension,
                "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "pixel_sha256": pixels}


def safe_filename(title):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip().rstrip(".")


def download(records, existing, workers):
    known_urls = {row["url"]: row for row in existing}

    def fetch(record):
        old = known_urls.get(record["url"])
        cached = False
        if old and (ROOT / old["file"]).is_file():
            data = (ROOT / old["file"]).read_bytes()
            cached = hashlib.sha256(data).hexdigest() == old["sha256"]
            if not cached:
                data = request(record["url"])
        else:
            data = request(record["url"])
        info = inspect_image(data)
        if "expected_width" in record and (info["width"], info["height"]) != (record["expected_width"], record["expected_height"]):
            raise ValueError("下载图片尺寸与来源接口不一致")
        if record["url"].split("?", 1)[0].lower().split("/revision/")[0].endswith(".png") and info["extension"] != ".png":
            raise ValueError("CDN 未返回 PNG 原图")
        if "expected_sha1" in record:
            # CDN 可能重写 PNG 元数据；保留源哈希、实际哈希和尺寸核对结果。
            info["source_sha1"] = (old.get("source_sha1", record["expected_sha1"]) if cached
                                   else hashlib.sha1(data).hexdigest())
            info["source_sha1_matches"] = info["source_sha1"] == record["expected_sha1"]
        info["source_sha256"] = old.get("source_sha256", info["sha256"]) if cached else info["sha256"]
        info["source_bytes"] = old.get("source_bytes", info["bytes"]) if cached else info["bytes"]
        return record, data, info

    by_pixels = {row["pixel_sha256"]: row for row in existing if (ROOT / row["file"]).is_file()}
    output, failures = [], []
    total = len(records)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, record): record for record in records}
        for n, future in enumerate(as_completed(futures), 1):
            record = futures[future]
            try:
                record, data, info = future.result()
                row = {**record, **info}
                duplicate = by_pixels.get(info["pixel_sha256"])
                if duplicate:
                    row.update({k: duplicate[k] for k in ("file", "sha256", "bytes")})
                    row["deduplicated"] = True
                else:
                    suffix = f"__{record['variant']}" if record.get("variant", 1) > 1 else ""
                    relative = Path(record["folder"]) / (safe_filename(record["title"]) + suffix + info["extension"])
                    target = ROOT / relative
                    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != info["sha256"]:
                        relative = relative.with_stem(relative.stem + "__" + info["sha256"][:8])
                        target = ROOT / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    temporary = target.with_suffix(target.suffix + ".part")
                    temporary.write_bytes(data)
                    temporary.replace(target)
                    row["file"] = relative.as_posix()
                    row["deduplicated"] = False
                    by_pixels[info["pixel_sha256"]] = row
                output.append(row)
            except Exception as exc:
                failures.append({"item": record, "error": str(exc)})
                print(f"下载 ERROR {record['title']}: {exc}", flush=True)
            if n % 50 == 0 or n == total:
                print(f"下载: {n}/{total}, unique={len(by_pixels)}, failed={len(failures)}", flush=True)
            if n % 100 == 0:
                write_json(ROOT / "manifest.json", existing + output)
    return output, failures


def finish(rows, failures):
    rows = sorted({r["url"]: r for r in rows}.values(), key=lambda r: (r["source"], r["title"], r["url"]))
    priority = {"米游社官方档案馆": 0, "BWIKI": 1, "Honkai Impact 3 Wiki": 2}
    seen_files = set()
    for row in sorted(rows, key=lambda r: (priority[r["source"]], r["title"])):
        row["deduplicated"] = row["file"] in seen_files
        seen_files.add(row["file"])
    write_json(ROOT / "manifest.json", rows)
    write_json(ROOT / "failures.json", failures)
    fields = ["source", "title", "file", "width", "height", "bytes", "deduplicated", "page", "url", "sha256", "pixel_sha256"]
    with (ROOT / "index.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    unique = {r["file"] for r in rows}
    report = {"downloaded_at": datetime.now(timezone.utc).isoformat(),
              "source_images": dict(Counter(r["source"] for r in rows)),
              "source_records": len(rows), "unique_files": len(unique),
              "total_bytes": sum((ROOT / f).stat().st_size for f in unique),
              "errors": len(failures),
              "download_failures": sum(isinstance(f.get("item"), dict) and "url" in f["item"] for f in failures),
              "missing_source_references": sum(f.get("error") == "来源目录引用了不存在的图片文件" for f in failures),
              "cdn_sha1_differences": sum(r.get("source_sha1_matches") is False for r in rows)}
    write_json(ROOT / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--refresh-details", action="store_true")
    parser.add_argument("--retry-failed", action="store_true", help="仅重试下载失败的图片")
    args = parser.parse_args()
    workers = max(1, min(args.workers, 8))
    ROOT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    old = read_json(ROOT / "manifest.json", [])
    if args.retry_failed:
        pending = read_json(ROOT / "failures.json", [])
        retry = [f["item"] for f in pending if isinstance(f.get("item"), dict) and "url" in f["item"]]
        unresolved = [f for f in pending if f.get("item") not in retry]
        more, failures = download(retry, old, workers)
        finish(old + more, unresolved + failures)
        return
    official, failures = official_images(workers, args.refresh_details)
    primary, errors = download(official, old, workers)
    failures += errors
    write_json(ROOT / "manifest.json", primary)
    supplements, errors = supplemental_images(workers)
    failures += errors
    more, errors = download(supplements, primary + old, workers)
    failures += errors
    finish(primary + more, failures)


if __name__ == "__main__":
    main()
