#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查离线站点内部链接与图片引用是否全部有效。"""
import os
import re
import sys

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    root = sys.argv[1]
    idx = open(os.path.join(root, "index.html"), encoding="utf-8").read()
    page_links = set(re.findall(r'href="(pages/[^"]+\.html)"', idx))
    img_links = set(re.findall(r'src="(images/[^"]+)"', idx))
    missing_pages = [p for p in page_links if not os.path.exists(os.path.join(root, p))]
    missing_imgs = [p for p in img_links if not os.path.exists(os.path.join(root, p))]

    bad_refs = []
    for fn in os.listdir(os.path.join(root, "pages")):
        if not fn.endswith(".html"):
            continue
        txt = open(os.path.join(root, "pages", fn), encoding="utf-8").read()
        for ref in re.findall(r'(?:src|href)="([^"]+)"', txt):
            if ref.startswith(("http", "#", "../index.html")):
                continue
            target = os.path.normpath(os.path.join(root, "pages", ref))
            if not os.path.exists(target):
                bad_refs.append((fn, ref))

    print(f"index -> pages: {len(page_links)} refs, missing {len(missing_pages)}")
    print(f"index -> images: {len(img_links)} refs, missing {len(missing_imgs)}")
    print(f"detail pages: broken refs {len(bad_refs)}")
    for x in bad_refs[:20]:
        print("  ", x)

if __name__ == "__main__":
    main()
