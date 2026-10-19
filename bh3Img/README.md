# 崩坏3圣痕图鉴图片

收集日期：2026-10-15。保存图鉴详情页提供的立绘原始尺寸文件，保留透明背景，不对图片进行重绘、缩放或格式转换。

本次核对完成：三处来源共 **1,966 个有效图片条目**，按实际像素去重后保存 **1,306 张图片**，合计 **670.4 MB**。有效图片下载失败数为 **0**。全部本地文件已核对 SHA256、文件大小及图片尺寸；官方目录 700 件全部对应到本地文件。详细结果见 `verification.json`。

## 图片位置

- 本目录的中文命名图片：米游社官方档案馆全部 **700 件圣痕**的立绘，包含上、中、下位及活动单件圣痕。
- `img/补充立绘`：BWIKI 中与已保存图片像素不同的文件。
- `img/补充立绘`：国际服 Wiki 中与已保存图片像素不同的文件，包含历史版本及其他立绘版本。

不同来源可能有相同人物、不同配色、裁剪、修订或压缩的图片。仅对尺寸及可见像素完全一致的图片去重，保留其他文件。重复来源条目通过清单的 `file` 字段指向同一张本地图片。

## 清单与核对

- `index.csv`：可用表格软件打开，按名称查看文件路径、尺寸和来源链接。
- `manifest.json`：完整下载清单、来源页面、图片 URL、文件 SHA256 和像素 SHA256。
- `report.json`：各来源条目数、去重后的图片总数和总大小。
- `failures.json`：来源失效引用及仍无法下载的条目。
- `metadata/official_catalog.json`：收集时的官方圣痕完整目录快照。

全部图片均检查文件格式及完整解码。补充来源还核对接口公布的原始尺寸。Fandom 使用 `format=original` 请求 PNG，避免 CDN 默认返回 WebP。部分 CDN 文件与接口记录的 SHA1 有差异，清单保留两者供核对；本地文件的 `sha256` 按实际保存字节计算。

BWIKI 图鉴中有三个引用对应的图片文件不存在：`布朗尼·迷城骇兔（中）.png`、`芽衣·暴怒（中）.png`、`西琳·蝼蚁.png`。前两件圣痕可在官方图片中找到；最后一项按来源失效引用记录。

## 来源

- [米游社：圣芙蕾雅档案馆 · 圣痕](https://bbs.mihoyo.com/bh3/wiki/channel/map/17/19)
- [BWIKI：圣痕图鉴](https://wiki.biligame.com/bh3/%E5%9C%A3%E7%97%95%E5%9B%BE%E9%89%B4)
- [Honkai Impact 3 Wiki：Stigmata Figures](https://honkaiimpact3.fandom.com/wiki/Category:Stigmata_Figures)

收集范围以以上公开目录为准。图片版权归原权利人所有，各文件的具体来源见清单。

## 再次下载

`download.py` 需要 Python 3.9 或以上及 Pillow。重跑会复用已有文件，刷新公开目录，并补充新条目。默认并发数为 6，支持失败重试与图片校验。

```sh
python3 download.py
python3 download.py --retry-failed
python3 download.py --refresh-details
```

`.cache/` 保存已解析的官方详情，供后续增量下载使用。
