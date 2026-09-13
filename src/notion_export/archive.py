"""ZIP 选择、安全解压和嵌套 Notion 导出展开。"""

from __future__ import annotations

import shutil
import stat
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

from .errors import ImportFailure


MAX_NESTED_ZIP_DEPTH = 8


MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024


def select_archive(project_root: Path, requested: Path | None) -> Path:
    if requested is not None:
        archive = requested.expanduser().resolve()
        if not archive.is_file():
            raise ImportFailure(f"ZIP 不存在：{archive}")
        if archive.suffix.lower() != ".zip":
            raise ImportFailure(f"输入文件不是 ZIP：{archive}")
        return archive

    archives = sorted(project_root.glob("*.zip"))
    if not archives:
        raise ImportFailure("项目根目录中没有 .zip 文件。")
    if len(archives) > 1:
        names = "\n  ".join(path.name for path in archives)
        raise ImportFailure(
            "项目根目录中有多个 ZIP，请显式指定要导入的文件：\n  " + names
        )
    return archives[0].resolve()


def safe_member_path(name: str) -> Path:
    normalized = name.replace("\\", "/")
    if "\x00" in normalized:
        raise ImportFailure("ZIP 成员名包含空字节。")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise ImportFailure(f"ZIP 包含不安全路径：{name}")
    return Path(*pure.parts)


def extract_zip_safely(archive: Path, destination: Path) -> None:
    try:
        with ZipFile(archive) as zip_file:
            infos = zip_file.infolist()
            total_size = sum(info.file_size for info in infos)
            if total_size > MAX_UNCOMPRESSED_BYTES:
                raise ImportFailure(
                    f"ZIP 解压后过大：{total_size} bytes，"
                    f"上限为 {MAX_UNCOMPRESSED_BYTES} bytes。"
                )

            for info in infos:
                relative = safe_member_path(info.filename)
                target = destination / relative
                unix_mode = info.external_attr >> 16
                if stat.S_ISLNK(unix_mode):
                    raise ImportFailure(f"ZIP 不允许包含符号链接：{info.filename}")

                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                if target.exists():
                    raise ImportFailure(f"多个压缩包产生了同名文件：{relative}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with zip_file.open(info) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                target.chmod(0o644)
    except BadZipFile as exc:
        raise ImportFailure(f"无效 ZIP：{archive}") from exc


def unpack_nested_export(archive: Path, workspace: Path) -> Path:
    """递归展开“外层 ZIP 仅包含 Part-N.zip”的 Notion 导出格式。"""
    current = workspace / "layer-0"
    current.mkdir()
    extract_zip_safely(archive, current)

    for depth in range(1, MAX_NESTED_ZIP_DEPTH + 1):
        macos_metadata = current / "__MACOSX"
        if macos_metadata.exists():
            shutil.rmtree(macos_metadata)

        entries = list(current.iterdir())
        wrapper_zips = [
            entry for entry in entries if entry.is_file() and entry.suffix.lower() == ".zip"
        ]
        if not entries or len(wrapper_zips) != len(entries):
            return current

        next_layer = workspace / f"layer-{depth}"
        next_layer.mkdir()
        for nested_archive in sorted(wrapper_zips):
            extract_zip_safely(nested_archive, next_layer)
        current = next_layer

    raise ImportFailure(f"嵌套 ZIP 超过 {MAX_NESTED_ZIP_DEPTH} 层。")
