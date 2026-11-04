"""允许 0.9～1.1 倍等比缩放的紧凑拼接，输出可编辑 PSD / PSB。

首次运行安装依赖：
    py -m pip install Pillow pillow-heif psd-tools==1.19.0
运行：
    py image_collage_scaled.py

仅扫描 IMAGE_DIR 直属图片，每张图片一个图层，不裁切、不旋转排布。
按统一缩放因子等比缩放，像素尺寸取整；校验对象是缩放后的图层像素。
按 EXIF 纠正照片显示方向；以 8 位 RGB/RGBA 解码，保留透明度。
等高行左对齐，图片之间无新增留白，剩余背景只在每行右端。
在接近目标比例的排布中尽量减少右侧空白，不保证数学全局最优。
大型图片合集需要较多内存和磁盘空间；PSD 超限时自动输出 PSB。
"""

# ======================= 在这里自定义 =======================
IMAGE_DIR = r"D:\Backup\Pictures\风堇"  # 图片根目录，也是输出目录
MIN_SCALE = 0.9
MAX_SCALE = 1.1
BACKGROUND_COLOR = "#e2b1ab"            # 支持带 / 不带 # 的六位十六进制颜色
TARGET_RATIO = 2.0                      # 期望宽 / 高比例
RATIO_TOLERANCE = 0.15                  # 允许上下浮动 15%，即 1.7～2.3
OPTIMIZE_SECONDS = 120                   # 搜索时长；增加可尝试更多排布
VERIFY_PIXELS = True                    # 保存后逐层验证尺寸、位置和像素
OUTPUT_PREFIX = "图片拼接_弹性缩放"      # 输出名称自动附加时间，避免覆盖
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
import json
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageOps
    from psd_tools import PSDImage
    from psd_tools.api.layers import PixelLayer
    from psd_tools.constants import Compression
    from psd_tools.psd import PSD
    from psd_tools.psd.image_resources import ImageResources
except ImportError as exc:
    raise SystemExit(
        "缺少依赖，请执行：\n"
        "py -m pip install Pillow pillow-heif psd-tools==1.19.0\n"
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
    """等高行排布：行内无缝，行间无缝，新增背景只在右侧。

    在 0.9～1.1 倍共同可行高度内等比缩放。搜索行分组和画布宽度，
    在接近目标比例的方案中降低空白率。不会为了比例在底部增加空白。
    图片原有的透明区域或空白不属于排布空隙。
    """
    if not items:
        raise ValueError('没有图片可以排列')
    original = [(i['width'], i['height']) for i in items]
    for item in items:
        item['original_width'] = item['width']
        item['original_height'] = item['height']
    n = len(items)
    area = sum(w*h for w,h in original)
    lower_ratio = target*(1-tolerance)
    upper_ratio = target*(1+tolerance)
    rng = random.Random(915)
    started = report = time.monotonic()
    best = None
    trials = 0
    nominal = math.sqrt(area*target)
    minimum_width = max(max(1,round(w*max(1,math.ceil(h*MIN_SCALE-1e-9))/h))
                        for w,h in original)

    def arrange(width, order, waste_weight):
        nonlocal best, trials
        # 动态规划：相邻的高度相近图片分成等高行。
        # 每行高度取共同合法范围内能放入给定宽度的最大整数。
        costs = [float('inf')]*(n+1)
        choices = [None]*n
        costs[n] = 0.0
        for start in range(n-1,-1,-1):
            min_height, max_height, aspects = 1, 300000, 0.0
            for end in range(start,n):
                idx = order[end]
                ow,oh = original[idx]
                min_height = max(min_height, math.ceil(oh*MIN_SCALE-1e-9))
                max_height = min(max_height, math.floor(oh*MAX_SCALE+1e-9))
                aspects += ow/oh
                if min_height > max_height:
                    break
                height = min(max_height, math.floor(width/aspects))
                if height < min_height:
                    break
                indices = order[start:end+1]
                widths = [max(1,round(original[k][0]*height/original[k][1])) for k in indices]
                used = sum(widths)
                # 处理多个整数宽度相加后可能多出的几个像素。
                while used > width and height >= min_height:
                    height -= 1
                    widths = [max(1,round(original[k][0]*height/original[k][1])) for k in indices]
                    used = sum(widths)
                if height < min_height:
                    continue
                cost = height*(1+waste_weight*(width-used)/width)+costs[end+1]
                if cost < costs[start]:
                    costs[start] = cost
                    choices[start] = (end+1,height,indices,widths,used)
        trials += 1
        if choices[0] is None:
            return
        rows = []
        start = 0
        while start < n:
            row = choices[start]
            if row is None:
                return
            start = row[0]
            rows.append(row)
        # 宽行在上，短行在下，留白形成连通的右侧区域。
        rows.sort(key=lambda row:row[4],reverse=True)
        height = sum(row[1] for row in rows)
        canvas_width = max(row[4] for row in rows)
        if canvas_width/height < lower_ratio:
            canvas_width = math.ceil(height*lower_ratio)
        if max(canvas_width,height)>300000:
            return
        content_area = sum(row[1]*row[4] for row in rows)
        ratio = canvas_width/height
        blank = 1-content_area/(canvas_width*height)
        # 极端单图可能不能满足近似比例；保持右侧留白规则，不额外补底边。
        ratio_deviation = max(0.0,ratio-upper_ratio)/target
        score = (ratio_deviation, blank, abs(ratio-target),canvas_width*height)
        if best is None or score < best[0]:
            best = (score,canvas_width,height,rows)

    base_order = sorted(range(n),key=lambda j:(-original[j][1],-original[j][0]))
    candidates = sorted({max(minimum_width,round(nominal*(.72+j*.025))) for j in range(35)})
    # 即使搜索时长为 0，也执行一轮初始化，确保有可行结果。
    for width in candidates:
        arrange(width,base_order,1.0)
        if best is not None and time.monotonic()-started>=seconds:
            break
    while time.monotonic()-started<seconds:
        if best is not None and rng.random()<.6:
            radius=max(1,round(best[1]*.10))
            width=max(minimum_width,best[1]+rng.randint(-radius,radius))
        else:
            width=max(minimum_width,round(nominal*rng.uniform(.7,1.7)))
        jitter=rng.choice([0,.01,.04,.08])
        priorities=[h*rng.uniform(1-jitter,1+jitter) for w,h in original]
        order=sorted(range(n),key=lambda j:(-priorities[j],-original[j][0]))
        arrange(width,order,rng.choice([0,.5,1,2,4]))
        if time.monotonic()-report>20 and best is not None:
            log(f'右侧留白搜索 {trials} 次，空白 {best[0][1]:.2%}')
            report=time.monotonic()
    if best is None:
        raise RuntimeError('没有找到满足缩放范围和 Photoshop 尺寸限制的行排布')
    _,w,h,rows=best
    y=0
    seen=set()
    for row_number,(_,rh,indices,widths,used) in enumerate(rows,1):
        x=0
        for idx,rw in zip(indices,widths):
            ow,oh=original[idx]
            scale=rh/oh
            if not MIN_SCALE-1e-9<=scale<=MAX_SCALE+1e-9:
                raise RuntimeError('缩放越界')
            if rw!=max(1,round(ow*scale)) or idx in seen:
                raise RuntimeError('图片尺寸不符或重复')
            items[idx].update(x=x,y=y,width=rw,height=rh,scale=scale,row=row_number)
            seen.add(idx)
            x+=rw
        if x!=used or x>w:
            raise RuntimeError('行内衔接检查失败')
        y+=rh
    if len(seen)!=n or y!=h:
        raise RuntimeError('图片缺失或行间衔接检查失败')
    log(f'最终：{w} × {h}，比例 {w/h:.3f}:1，空白 {best[0][1]:.2%}（仅在右侧）')
    return w,h


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
            if image.size != (item['original_width'], item['original_height']):
                raise RuntimeError("图片尺寸发生变化，请重新运行。")
            if image.size != (item['width'], item['height']):
                resized=image.resize((item['width'],item['height']),Image.Resampling.LANCZOS)
                image.close()
                image=resized
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
        manifest = dict(width=w,height=h,background=BACKGROUND_COLOR,layout='left_aligned_rows_right_blank',
                        blank_fraction=1-area/(w*h),
                        images=[dict(name=i['path'].name,x=i['x'],y=i['y'],
                                     width=i['width'],height=i['height'],
                                     original_width=i['original_width'],original_height=i['original_height'],
                                     scale=i['scale'],row=i['row']) for i in items])
        destination.with_suffix('.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
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
    if not 0 < MIN_SCALE <= 1 <= MAX_SCALE:
        raise ValueError("缩放范围须包含 1，例如 0.9～1.1。")
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
