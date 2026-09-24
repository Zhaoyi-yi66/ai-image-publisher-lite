from __future__ import annotations

import io
import re
from dataclasses import dataclass, replace
from pathlib import Path

from PIL import Image, ImageCms, ImageOps


CUSTOM_PRESET_NAME = "自定义尺寸"
PRESETS = {
    "原图尺寸（默认）": "original",
    CUSTOM_PRESET_NAME: "custom",
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
    crop_anchor: str = "居中"
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
        return _pixels_only(image)


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
    crop_anchor: str = "居中",
) -> Image.Image:
    if target == "original":
        return image.copy()

    if target is None:
        copy = image.copy()
        copy.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        return copy

    if mode == "裁切":
        centering = {
            "居中": (0.5, 0.5),
            "上方": (0.5, 0.0),
            "下方": (0.5, 1.0),
            "左侧": (0.0, 0.5),
            "右侧": (1.0, 0.5),
        }.get(crop_anchor, (0.5, 0.5))
        return ImageOps.fit(
            image,
            target,
            method=Image.Resampling.LANCZOS,
            centering=centering,
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

    image = _pixels_only(image)
    image.save(output, format=output_format, **save_options)
    return output.getvalue()


def _pixels_only(image: Image.Image) -> Image.Image:
    """Rebuild an image from pixels so container metadata is not carried forward."""
    normalized = image.convert("RGBA" if image.mode == "RGBA" else "RGB")
    return Image.frombytes(normalized.mode, normalized.size, normalized.tobytes())


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
    custom_size: tuple[int, int] | None = None,
) -> tuple[str, bytes]:
    output_format = source_format(source) if options.output_format.upper() == "SOURCE" else options.output_format.upper()
    resolved_options = replace(options, output_format=output_format)
    image = normalize_image(source)
    target = PRESETS[preset_name]
    if target == "custom":
        if custom_size is None:
            raise ValueError("请选择有效的自定义尺寸")
        if not all(16 <= value <= 20000 for value in custom_size):
            raise ValueError("自定义宽高需在 16–20000 像素之间")
        target = custom_size
    resized = resize_for_preset(
        image,
        target,
        options.mode,
        options.background,
        options.crop_anchor,
    )
    content = encode_image(resized, resolved_options)
    preset_slug = {
        "原图尺寸（默认）": "processed",
        CUSTOM_PRESET_NAME: f"custom_{custom_size[0]}x{custom_size[1]}" if custom_size else "custom",
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

