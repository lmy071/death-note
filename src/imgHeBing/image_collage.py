"""原尺寸图片紧凑拼接，输出可编辑 PSD / PSB（Python 3.10+）。

首次运行安装依赖：
    py -m pip install Pillow pillow-heif rectpack==0.2.2 psd-tools==1.19.0
运行：
    py image_collage.py

仅扫描 IMAGE_DIR 直属图片，每张图片一个图层，不裁切、不缩放、不旋转排布。
按 EXIF 纠正照片显示方向；以 8 位 RGB/RGBA 解码，保留透明度。
优化属于启发式搜索，选择已搜索方案中面积最小的结果，不保证数学全局最优。
大型图片合集需要较多内存和磁盘空间；PSD 超限时自动输出 PSB。
"""

# ======================= 在这里自定义 =======================
IMAGE_DIR = r"D:\Backup\Pictures\花火&火花"  # 图片根目录，也是输出目录
BACKGROUND_COLOR = "#c14e53"            # 支持带 / 不带 # 的六位十六进制颜色
TARGET_RATIO = 2.0                      # 期望宽 / 高比例
RATIO_TOLERANCE = 0.15                  # 允许上下浮动 15%，即 1.7～2.3
OPTIMIZE_SECONDS = 200                   # 搜索时长；增加可尝试更多排布
VERIFY_PIXELS = True                    # 保存后逐层验证尺寸、位置和像素
OUTPUT_PREFIX = "图片拼接"              # 输出名称自动附加时间，避免覆盖
# ===========================================================

import gc
import hashlib
import math
import random
import re
import struct
import sys
import time
import zlib
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageOps
    from rectpack import (newPacker, MaxRectsBssf, MaxRectsBaf,
                          MaxRectsBl, MaxRectsBlsf, SORT_NONE)
    from psd_tools import PSDImage
    from psd_tools.api.layers import PixelLayer
    from psd_tools.constants import Compression
    from psd_tools.psd import PSD
    from psd_tools.psd.image_resources import ImageResources
except ImportError as exc:
    raise SystemExit(
        "缺少依赖，请执行：\n"
        "py -m pip install Pillow pillow-heif rectpack==0.2.2 psd-tools==1.19.0\n"
        f"详细信息：{exc}"
    ) from exc

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pillow_heif = None

Image.MAX_IMAGE_PIXELS = None  # 本工具专门处理用户指定的大图
EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp",
              ".bmp", ".tif", ".tiff", ".avif", ".gif"}


def log(message):
    print(message, flush=True)


def read_inputs(root):
    if not root.is_dir():
        raise ValueError(f"图片目录不存在：{root}")
    items = []
    for path in sorted(root.iterdir(), key=lambda p: p.name.casefold()):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue
        if path.suffix.lower() in {".heic", ".heif"} and pillow_heif is None:
            raise ValueError("检测到 HEIC/HEIF 图片，请先安装 pillow-heif")
        try:
            with Image.open(path) as im:
                if getattr(im, "n_frames", 1) > 1:
                    log(f"提示：{path.name} 为多帧图片，仅使用第一帧。")
                w, h = im.size
                if im.getexif().get(274) in (5, 6, 7, 8):
                    w, h = h, w
        except Exception as exc:
            raise ValueError(f"无法读取图片 {path.name}：{exc}") from exc
        stat = path.stat()
        items.append(dict(path=path, width=w, height=h,
                          stamp=(stat.st_size, stat.st_mtime_ns)))
    if not items:
        raise ValueError("根目录没有可读取的图片；不会扫描子目录。")
    return items


def optimize(items, seconds, target, tolerance):
    area = sum(i['width'] * i['height'] for i in items)
    low_ratio, high_ratio = target * (1 - tolerance), target * (1 + tolerance)
    max_w = max(i['width'] for i in items)
    max_h = max(i['height'] for i in items)
    rng = random.Random(8192)
    started = report = time.monotonic()
    best = None
    trials = 0
    algorithms = [MaxRectsBssf, MaxRectsBaf, MaxRectsBl, MaxRectsBlsf]

    def evaluate(width, height, order, algorithm, transpose=False):
        nonlocal best, trials
        if width < max_w or height < max_h:
            return False
        packer = newPacker(rotation=False, pack_algo=algorithm, sort_algo=SORT_NONE)
        for idx in order:
            item = items[idx]
            a, b = item['width'], item['height']
            packer.add_rect(b if transpose else a, a if transpose else b, rid=idx)
        packer.add_bin(height if transpose else width, width if transpose else height)
        packer.pack()
        trials += 1
        rects = packer.rect_list()
        if len(rects) != len(items):
            return False
        if transpose:
            rects = [(bn, y, x, rh, rw, idx) for bn, x, y, rw, rh, idx in rects]
        w = max(x + rw for _, x, y, rw, rh, idx in rects)
        h = max(y + rh for _, x, y, rw, rh, idx in rects)
        # 必要时增加画布，不改变原图，以满足允许的比例区间。
        if w / h < low_ratio:
            w = math.ceil(h * low_ratio)
        elif w / h > high_ratio:
            h = math.ceil(w / high_ratio)
        if best is None or w * h < best[0] * best[1]:
            best = (w, h, rects)
        return True

    order = sorted(range(len(items)),
                   key=lambda j: items[j]['width'] * items[j]['height'], reverse=True)
    # 总能放下的起点，保证单图、少量图片、极端尺寸也能生成。
    evaluate(sum(i['width'] for i in items), max_h, order, algorithms[0])
    widths = {max(max_w, round(math.sqrt(area * (low_ratio +
                    (high_ratio - low_ratio) * j / 12)))) for j in range(13)}
    for item in items:
        unit = item['width']
        count = max(1, round(math.sqrt(area * target) / unit))
        for n in (count - 1, count, count + 1):
            if n > 0:
                widths.add(max(max_w, n * unit))
    # 限制初始化候选数；尺寸选择不依赖具体相机或图片数量。
    widths = sorted(widths, key=lambda w: abs(w - math.sqrt(area * target)))[:48]
    for width in widths:
        if time.monotonic() - started >= seconds:
            break
        for algorithm in algorithms[:2]:
            for transpose in (False, True):
                lo = max(max_h - 1, math.ceil(area / width) - 1)
                hi = max(max_h, math.ceil(area / width * 1.3))
                if not evaluate(width, hi, order, algorithm, transpose):
                    continue
                while hi - lo > 1:
                    mid = (hi + lo) // 2
                    if evaluate(width, mid, order, algorithm, transpose):
                        hi = mid
                    else:
                        lo = mid

    while time.monotonic() - started < seconds and best[0] * best[1] > area:
        if rng.random() < .6:
            radius = max(1, round(best[0] * .035))
            width = max(max_w, best[0] + rng.randint(-radius, radius))
        else:
            width = max(max_w, round(math.sqrt(area * rng.uniform(low_ratio, high_ratio))
                                    * rng.uniform(.98, 1.08)))
        height = (best[0] * best[1] - 1) // width
        exponent = rng.uniform(0, 2)
        noise = rng.choice([0, .03, .15, .5, .95])
        scores = [i['width'] ** exponent * i['height'] ** (2 - exponent)
                  * rng.uniform(1 - noise, 1 + noise) for i in items]
        order = sorted(range(len(items)), key=lambda j: scores[j], reverse=True)
        evaluate(width, height, order, rng.choice(algorithms), rng.choice([True, False]))
        if time.monotonic() - report > 20:
            log(f"已搜索 {trials} 次，当前空白：{1 - area / (best[0] * best[1]):.2%}")
            report = time.monotonic()

    w, h, rects = best
    if max(w, h) > 300000:
        raise ValueError("拼接尺寸超过 Photoshop 的 300000 像素上限。")
    if len({r[5] for r in rects}) != len(items):
        raise RuntimeError("排布检查失败：图片缺失或重复")
    for j, (_, x, y, rw, rh, idx) in enumerate(rects):
        if (rw, rh) != (items[idx]['width'], items[idx]['height']):
            raise RuntimeError("排布检查失败：原尺寸发生改变")
        if not (0 <= x and 0 <= y and x + rw <= w and y + rh <= h):
            raise RuntimeError("排布检查失败：图片超出画布")
        for _, xx, yy, ww, hh, _ in rects[:j]:
            if not (x + rw <= xx or xx + ww <= x or y + rh <= yy or yy + hh <= y):
                raise RuntimeError("排布检查失败：图片重叠")
        items[idx].update(x=x, y=y)
    log(f"排布：{w} × {h}，比例 {w/h:.3f}:1，空白 {1-area/(w*h):.2%}")
    return w, h


def solid_channel(value, count):
    compressor = zlib.compressobj(1)
    chunks = []
    for offset in range(0, count, 1048576):
        chunks.append(compressor.compress(bytes([value]) * min(1048576, count-offset)))
    chunks.append(compressor.flush())
    return b''.join(chunks)


def write_document(items, root, background, w, h):
    area = sum(i['width'] * i['height'] for i in items)
    # 保守估算 ZIP 图层和 RAW 合成图的体积；接近 2GB 时优先使用 PSB。
    bound = 4 * area * 1.01 + 3 * w * h + 64 * 1024**2
    version = 2 if max(w, h) > 30000 or bound >= 2_000_000_000 else 1
    extension = '.psb' if version == 2 else '.psd'
    destination = root / (OUTPUT_PREFIX + '_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + extension)
    temporary = destination.with_suffix(extension + '.partial')
    header = PSDImage._make_header('RGB', (w, h), 8)
    header.version = version
    doc = PSDImage(PSD(header=header, image_resources=ImageResources.new()))
    bg = PixelLayer.frompil(Image.new('RGB', (1, 1), background), doc,
                            name='Background', compression=Compression.ZIP)
    bg.name = '背景 #' + ''.join(f'{v:02X}' for v in background)
    bg._record.right, bg._record.bottom = w, h
    for info, channel in zip(bg._record.channel_info, bg._channels):
        value = 255 if int(info.id) == -1 else background[int(info.id)]
        channel.data = solid_channel(value, w * h)
        info.length = len(channel.data) + 2
    canvas = Image.new('RGB', (w, h), background)
    try:
        for n, item in enumerate(items, 1):
            stat = item['path'].stat()
            if (stat.st_size, stat.st_mtime_ns) != item['stamp']:
                raise RuntimeError(f"处理期间图片发生变化：{item['path'].name}，请重新运行。")
            with Image.open(item['path']) as src:
                oriented = ImageOps.exif_transpose(src)
                image = oriented.convert('RGBA')
                oriented.close()
            if image.size != (item['width'], item['height']):
                raise RuntimeError("图片尺寸发生变化，请重新运行。")
            alpha = image.getchannel('A')
            canvas.paste(image, (item['x'], item['y']), alpha)
            rgb = image.convert('RGB')
            layer = PixelLayer.frompil(rgb, doc, name=f'Image {n}',
                                      top=item['y'], left=item['x'], compression=Compression.ZIP)
            rgb.close()
            layer.name = item['path'].name[:255]
            # 直接写入透明通道，保持 RGB 文档中各图片的原始透明度。
            for info, channel in zip(layer._record.channel_info, layer._channels):
                if int(info.id) == -1:
                    channel.set_data(alpha.tobytes(), image.width, image.height, 8, version)
                    info.length = len(channel.data) + 2
            item['digest'] = hashlib.sha256(image.tobytes()).digest()
            image.close()
            alpha.close()
            if n % 10 == 0 or n == len(items):
                log(f"图层：{n}/{len(items)}")
        doc._update_record()
        log(f"正在保存 {extension.upper()[1:]} 到图片根目录……")
        with temporary.open('xb') as fp:
            record = doc._record
            record.header.write(fp)
            record.color_mode_data.write(fp)
            record.image_resources.write(fp)
            record.layer_and_mask_information.write(fp, version=version)
            # 使用 RAW 合成图，修复 Photoshop 27.10 对 ZIP 合成预览的不兼容。
            fp.write(struct.pack('>H', 0))
            for band in range(3):
                for top in range(0, h, 128):
                    strip = canvas.crop((0, top, w, min(h, top+128)))
                    plane = strip.getchannel(band)
                    fp.write(plane.tobytes())
                    plane.close()
                    strip.close()
        canvas.close()
        del doc, record, bg, layer
        gc.collect()
        if VERIFY_PIXELS:
            log("正在重新读取文件并校验每个图层……")
            check = PSDImage.open(temporary)
            if check.size != (w, h) or len(check) != len(items) + 1:
                raise RuntimeError("保存校验失败：画布尺寸或图层数不符")
            for layer, item in zip(list(check)[1:], items):
                expected = (item['x'], item['y'], item['x']+item['width'], item['y']+item['height'])
                if layer.bbox != expected or layer.name != item['path'].name[:255]:
                    raise RuntimeError(f"图层校验失败：{item['path'].name}")
                pixels = layer.topil().convert('RGBA')
                if hashlib.sha256(pixels.tobytes()).digest() != item['digest']:
                    raise RuntimeError(f"像素校验失败：{item['path'].name}")
                pixels.close()
            del check
            gc.collect()
        temporary.rename(destination)
    except BaseException:
        canvas.close()
        # 仅移除本次运行的未完成输出；不修改源图或已有成品。
        if temporary.exists():
            temporary.unlink()
        raise
    return destination


def main():
    color = BACKGROUND_COLOR.strip().lstrip('#')
    if not re.fullmatch(r'[0-9a-fA-F]{6}', color):
        raise ValueError("BACKGROUND_COLOR 必须是六位十六进制颜色，如 #95ADC7")
    if TARGET_RATIO <= 0 or not 0 <= RATIO_TOLERANCE < 1 or OPTIMIZE_SECONDS < 0:
        raise ValueError("请检查比例、浮动范围和搜索时长设置。")
    if not OUTPUT_PREFIX or re.search(r'[<>:"/\\|?*]', OUTPUT_PREFIX):
        raise ValueError("OUTPUT_PREFIX 必须是有效的文件名，不能包含路径。")
    root = Path(IMAGE_DIR).expanduser().resolve()
    items = read_inputs(root)
    log(f"读取 {len(items)} 张根目录图片（不含子目录）。")
    w, h = optimize(items, OPTIMIZE_SECONDS, TARGET_RATIO, RATIO_TOLERANCE)
    background = tuple(int(color[j:j+2], 16) for j in (0, 2, 4))
    output = write_document(items, root, background, w, h)
    log(f"完成：{output}\n文件大小：{output.stat().st_size / 1024**3:.2f} GiB")


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f"生成失败：{error}", file=sys.stderr)
        sys.exit(1)
