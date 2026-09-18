from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageCms, ImageOps


PRESETS = {
    "原图尺寸（默认）": "original",
    "Instagram 竖版 (1080×1350)": (1080, 1350),
    "TikTok 竖版 (1080×1920)": (1080, 1920),
    "YouTube 封面 (1280×720)": (1280, 720),
    "小红书竖版 (1080×1440)": (1080, 1440),
    "Web（长边 1600px）": None,
}

FORMAT_EXTENSIONS = {"JPEG": "jpg", "WEBP": "webp", "PNG": "png"}


@dataclass(frozen=True)
class ProcessOptions:
    mode: str = "留白"
    output_format: str = "SOURCE"
    quality: int = 90
    png_compress_level: int = 6
    background: tuple[int, int, int] = (255, 255, 255)


def safe_stem(filename: str) -> str:
    stem = Path(filename).stem.strip()
    cleaned = re.sub(r"[^\w\-\u4e00-\u9fff]+", "_", stem, flags=re.UNICODE)
    return cleaned.strip("_") or "image"


def normalize_image(source: bytes) -> Image.Image:
    with Image.open(io.BytesIO(source)) as opened:
        try:
            image = ImageOps.exif_transpose(opened)
        except (OSError, SyntaxError, ValueError):
            image = opened.copy()
        image.load()
        image = _to_srgb(image)
        return image.copy()


def source_format(source: bytes) -> str:
    with Image.open(io.BytesIO(source)) as image:
        detected = (image.format or "").upper()
    if detected == "JPG":
        detected = "JPEG"
    if detected not in FORMAT_EXTENSIONS:
        raise ValueError("无法识别原图片格式")
    return detected


def _to_srgb(image: Image.Image) -> Image.Image:
    icc_profile = image.info.get("icc_profile")
    has_alpha = image.mode in ("RGBA", "LA") or "transparency" in image.info

    if icc_profile:
        try:
            source_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_profile))
            target_profile = ImageCms.createProfile("sRGB")
            output_mode = "RGBA" if has_alpha else "RGB"
            return ImageCms.profileToProfile(
                image.convert(output_mode),
                source_profile,
                target_profile,
                outputMode=output_mode,
            )
        except (OSError, ValueError, ImageCms.PyCMSError):
            pass

    return image.convert("RGBA" if has_alpha else "RGB")


def resize_for_preset(
    image: Image.Image,
    target: tuple[int, int] | None | str,
    mode: str,
    background: tuple[int, int, int],
) -> Image.Image:
    if target == "original":
        return image.copy()

    if target is None:
        copy = image.copy()
        copy.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        return copy

    if mode == "裁切":
        return ImageOps.fit(
            image,
            target,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )

    contained = ImageOps.contain(image, target, Image.Resampling.LANCZOS)
    canvas_mode = "RGBA" if contained.mode == "RGBA" else "RGB"
    canvas_color = (*background, 255) if canvas_mode == "RGBA" else background
    canvas = Image.new(canvas_mode, target, canvas_color)
    position = ((target[0] - contained.width) // 2, (target[1] - contained.height) // 2)
    if contained.mode == "RGBA":
        canvas.alpha_composite(contained, position)
    else:
        canvas.paste(contained, position)
    return canvas


def encode_image(image: Image.Image, options: ProcessOptions) -> bytes:
    output = io.BytesIO()
    output_format = options.output_format.upper()
    save_options: dict[str, object] = {}

    if output_format == "JPEG":
        image = _flatten_alpha(image, options.background).convert("RGB")
        save_options.update(quality=options.quality, optimize=True, progressive=True)
    elif output_format == "WEBP":
        save_options.update(quality=options.quality, method=6)
    elif output_format == "PNG":
        save_options.update(compress_level=options.png_compress_level, optimize=True)
    else:
        raise ValueError(f"不支持的输出格式：{options.output_format}")

    image.save(output, format=output_format, **save_options)
    return output.getvalue()


def _flatten_alpha(image: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    if image.mode != "RGBA":
        return image
    base = Image.new("RGB", image.size, background)
    base.paste(image, mask=image.getchannel("A"))
    return base


def process_one(
    source: bytes,
    filename: str,
    preset_name: str,
    options: ProcessOptions,
) -> tuple[str, bytes]:
    output_format = source_format(source) if options.output_format.upper() == "SOURCE" else options.output_format.upper()
    resolved_options = replace(options, output_format=output_format)
    image = normalize_image(source)
    resized = resize_for_preset(image, PRESETS[preset_name], options.mode, options.background)
    content = encode_image(resized, resolved_options)
    preset_slug = {
        "原图尺寸（默认）": "processed",
        "Instagram 竖版 (1080×1350)": "instagram_1080x1350",
        "TikTok 竖版 (1080×1920)": "tiktok_1080x1920",
        "YouTube 封面 (1280×720)": "youtube_1280x720",
        "小红书竖版 (1080×1440)": "xiaohongshu_1080x1440",
        "Web（长边 1600px）": "web_1600",
    }[preset_name]
    if options.output_format.upper() == "SOURCE":
        source_extension = Path(filename).suffix.lower().lstrip(".")
        extension = source_extension if source_extension in {"jpg", "jpeg", "png", "webp"} else FORMAT_EXTENSIONS[output_format]
    else:
        extension = FORMAT_EXTENSIONS[output_format]
    return f"{safe_stem(filename)}_{preset_slug}.{extension}", content


def build_zip(files: Iterable[tuple[str, bytes]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        used_names: set[str] = set()
        for filename, content in files:
            unique_name = _unique_name(filename, used_names)
            used_names.add(unique_name)
            archive.writestr(unique_name, content)
    return output.getvalue()


def _unique_name(filename: str, used_names: set[str]) -> str:
    if filename not in used_names:
        return filename
    path = Path(filename)
    counter = 2
    while True:
        candidate = f"{path.stem}_{counter}{path.suffix}"
        if candidate not in used_names:
            return candidate
        counter += 1

