import tempfile
import unittest
from pathlib import Path

from PIL import Image

from app import ImagePublisherApp


class AppHelperTests(unittest.TestCase):
    def test_original_size_is_selected_by_default(self):
        app = ImagePublisherApp()
        app.root.withdraw()
        try:
            self.assertTrue(app.preset_vars["原图尺寸（默认）"].get())
            self.assertEqual(sum(variable.get() for variable in app.preset_vars.values()), 1)
            app._set_all_presets(True)
            self.assertTrue(all(variable.get() for variable in app.preset_vars.values()))
            app._set_all_presets(False)
            self.assertFalse(any(variable.get() for variable in app.preset_vars.values()))
        finally:
            app.root.destroy()

    def test_duplicate_output_names_get_suffix(self):
        used_names = {"photo_instagram.jpg"}
        result = ImagePublisherApp._unique_output_name("photo_instagram.jpg", used_names)
        self.assertEqual(result, "photo_instagram_2.jpg")

    def test_existing_output_file_gets_suffix(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            directory = Path(temp_directory)
            (directory / "photo_processed.png").write_bytes(b"existing")
            result = ImagePublisherApp._unique_output_name("photo_processed.png", set(), directory)
            self.assertEqual(result, "photo_processed_2.png")

    def test_existing_result_folder_gets_suffix(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            folder = Path(temp_directory) / "AI图片处理结果"
            folder.mkdir()
            result = ImagePublisherApp._available_folder(folder)
            self.assertEqual(result.name, "AI图片处理结果_2")

    def test_dropped_folder_adds_supported_images(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            directory = Path(temp_directory)
            Image.new("RGB", (20, 20), "blue").save(directory / "one.png")
            (directory / "note.txt").write_text("ignore", encoding="utf-8")
            app = ImagePublisherApp()
            app.root.withdraw()
            try:
                app._add_files([directory])
                self.assertEqual([path.name for path in app.files], ["one.png"])
            finally:
                app.root.destroy()


if __name__ == "__main__":
    unittest.main()

