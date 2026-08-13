from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "smart-video"
BUILDER_PATH = (
    PLUGIN_ROOT / "skills" / "smart-video" / "scripts" / "build_slide_master.py"
)


def _load_builder():
    spec = importlib.util.spec_from_file_location("smart_video_slide_master", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Smart Video Slide MASTER builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SmartVideoSlideArtDirectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = _load_builder()

    def _art_direction(self) -> dict[str, object]:
        return {
            "schema_id": "smart-video.slide-art-direction.v1",
            "version": 1,
            "video_id": "video-01",
            "whole_video": "Use one restrained editorial visual language.",
            "slides": [
                {
                    "shot_id": "shot-01",
                    "design_direction": "Use one dominant comparison anchor.",
                },
                {
                    "shot_id": "shot-03",
                    "design_direction": "Resolve the supplied process as a directional rail.",
                },
            ],
        }

    @staticmethod
    def _base_master() -> str:
        return """## Slide Visual System

### Visual Language
- Style: Editorial Grid / Magazine

### Palette
| Role | Hex |
| --- | --- |
| Primary | `#2457D6` |
| Highlight | `#F0C419` |
| Background | `#FAFAF8` |
| Foreground | `#171717` |
| Danger | `#B42318` |
"""

    def test_builder_uses_versioned_art_direction_contract(self) -> None:
        self.assertEqual(self.builder.SCHEMA_ID, "smart-video.slide-master-input.v2")
        self.assertEqual(self.builder.MASTER_SCHEMA_ID, "smart-video.slide-design-master.v2")
        self.builder.validate_art_direction(
            self._art_direction(),
            "video-01",
            ["shot-01", "shot-03"],
        )

    def test_art_direction_must_bind_to_video_and_ordered_slides(self) -> None:
        wrong_video = self._art_direction()
        wrong_video["video_id"] = "video-02"
        with self.assertRaisesRegex(self.builder.BuildError, "must match input.video_id"):
            self.builder.validate_art_direction(
                wrong_video,
                "video-01",
                ["shot-01", "shot-03"],
            )

        wrong_order = self._art_direction()
        wrong_order["slides"] = list(reversed(wrong_order["slides"]))
        with self.assertRaisesRegex(self.builder.BuildError, "must match input Slide order"):
            self.builder.validate_art_direction(
                wrong_order,
                "video-01",
                ["shot-01", "shot-03"],
            )

    def test_art_direction_is_embedded_in_master_with_its_hash(self) -> None:
        art_direction = self._art_direction()
        payload = {"video_id": "video-01", "art_direction": art_direction}
        master = self.builder.compose_master(
            payload,
            {"version": "test"},
            self._base_master(),
            "Editorial Grid / Magazine",
            [],
        )
        expected_hash = self.builder.sha256_bytes(
            self.builder.canonical_bytes(art_direction)
        )
        self.assertIn('"schema_id":"smart-video.slide-design-master.v2"', master)
        self.assertIn(f'"art_direction_sha256":"{expected_hash}"', master)
        self.assertIn("## Slide Art Direction", master)
        self.assertIn("`shot-03`: Resolve the supplied process", master)

    def test_portrait_master_uses_the_confirmed_canvas_and_safe_area(self) -> None:
        payload = {
            "video_id": "video-01",
            "brief": {"aspect_ratio": "9:16"},
            "art_direction": self._art_direction(),
        }
        master = self.builder.compose_master(
            payload,
            {"version": "test"},
            self._base_master(),
            "Editorial Grid / Magazine",
            [],
        )

        self.assertIn('"aspect_ratio":"9:16"', master)
        self.assertIn('"canvas_px":{"height":1920,"width":1080}', master)
        self.assertIn('"safe_area_px":{"bottom":96,"left":54,"right":54,"top":96}', master)
        self.assertIn("fixed 9:16 video canvas at 1080x1920", master)

    def test_rgba_palette_roles_are_composited_against_background(self) -> None:
        self.assertEqual(
            self.builder.normalize_palette_color(
                "rgba(255, 0, 0, 0.5)",
                "Accent",
                background="#000000",
            ),
            "#800000",
        )
        with self.assertRaisesRegex(self.builder.BuildError, "requires an opaque background"):
            self.builder.normalize_palette_color("rgba(0, 0, 0, 0.5)", "Background")


if __name__ == "__main__":
    unittest.main()
