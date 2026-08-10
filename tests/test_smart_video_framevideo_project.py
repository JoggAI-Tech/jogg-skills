import tempfile
import unittest
from pathlib import Path

from smartvideo_test_runtime import RUNTIME_ROOT  # noqa: F401

from backend.services import framevideo_project  # noqa: E402


class FrameVideoProjectMarkupTests(unittest.TestCase):
    def test_broll_is_muted_by_default_and_remains_editor_controllable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            framevideo_project._write_index(
                destination,
                title="B-roll audio default",
                width=1920,
                height=1080,
                duration=3.0,
                scenes=[
                    {
                        "shot_id": "shot-01",
                        "start_seconds": 0.0,
                        "duration_seconds": 3.0,
                        "visual_file": "assets/visual/shot-01.mp4",
                        "audio_file": "",
                        "visual_kind": "broll",
                    }
                ],
            )

            document = (destination / "index.html").read_text(encoding="utf-8")

        self.assertIn("smart-video-broll", document)
        self.assertIn('data-has-audio="false" muted', document)


if __name__ == "__main__":
    unittest.main()
