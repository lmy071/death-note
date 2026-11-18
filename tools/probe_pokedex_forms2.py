#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""稳健探测：记录每个候选 ID 的最终状态（200/404），带重试，避免网络抖动造成漏判。"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
BASE = "https://dex.pokemon.cn/play/pokedex/"

def probe(eid, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(BASE + eid, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                return eid, 200
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return eid, 404
            last = e.code
        except Exception as e:  # noqa: BLE001
            last = "err"
        time.sleep(0.6 * (i + 1))
    return eid, last

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-sub", type=int, default=6)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    targets = [f"{b:04d}_{s}" for b in range(1, 1026) for s in range(1, args.max_sub + 1)]
    result = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, (eid, st) in enumerate(ex.map(probe, targets), 1):
            result[eid] = st
            if i % 250 == 0:
                found = sum(1 for v in result.values() if v == 200)
                errs = sum(1 for v in result.values() if v not in (200, 404))
                print(f"probed {i}/{len(targets)} 200={found} err={errs}", flush=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    ok = [k for k, v in result.items() if v == 200]
    err = [k for k, v in result.items() if v not in (200, 404)]
    print(f"200={len(ok)} 404={sum(1 for v in result.values() if v == 404)} err={len(err)}")
    if err:
        print("err ids:", err[:40])

if __name__ == "__main__":
    main()
