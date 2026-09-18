import io
import unittest

from PIL import Image

from image_processor import PRESETS, ProcessOptions, process_one


class ImageProcessorTests(unittest.TestCase):
    def test_xiaohongshu_preset_uses_1080_by_1440(self):
        self.assertEqual(PRESETS["小红书竖版 (1080×1440)"], (1080, 1440))

    def make_image(self, size=(640, 480), mode="RGB"):
        image = Image.new(mode, size, (40, 120, 200, 128) if mode == "RGBA" else (40, 120, 200))
        output = io.BytesIO()
        exif = Image.Exif()
        exif[271] = "Test Camera Brand"
        exif[272] = "Test Device Model"
        image.save(output, format="PNG", exif=exif)
        return output.getvalue()

    def test_all_fixed_presets_have_exact_dimensions(self):
        source = self.make_image()
        options = ProcessOptions(mode="留白", output_format="JPEG")
        for preset_name, target in PRESETS.items():
            if not isinstance(target, tuple):
                continue
            _, content = process_one(source, "示例.png", preset_name, options)
            with Image.open(io.BytesIO(content)) as image:
                self.assertEqual(image.size, target)
                self.assertNotIn("exif", image.info)

    def test_web_preset_limits_long_edge(self):
        source = self.make_image((2400, 1200))
        options = ProcessOptions(output_format="WEBP")
        _, content = process_one(source, "wide.png", "Web（长边 1600px）", options)
        with Image.open(io.BytesIO(content)) as image:
            self.assertEqual(image.size, (1600, 800))

    def test_alpha_image_can_export_to_jpeg(self):
        source = self.make_image(mode="RGBA")
        options = ProcessOptions(output_format="JPEG")
        _, content = process_one(source, "alpha.png", "YouTube 封面 (1280×720)", options)
        with Image.open(io.BytesIO(content)) as image:
            self.assertEqual(image.mode, "RGB")

    def test_original_size_and_format_are_preserved_by_default(self):
        source = self.make_image((733, 511))
        filename, content = process_one(source, "示例.png", "原图尺寸（默认）", ProcessOptions())
        self.assertEqual(filename, "示例_processed.png")
        with Image.open(io.BytesIO(content)) as image:
            self.assertEqual(image.size, (733, 511))
            self.assertEqual(image.format, "PNG")

    def test_selected_format_changes_extension(self):
        source = self.make_image()
        filename, _ = process_one(source, "示例.png", "原图尺寸（默认）", ProcessOptions(output_format="WEBP"))
        self.assertEqual(filename, "示例_processed.webp")


if __name__ == "__main__":
    unittest.main()

