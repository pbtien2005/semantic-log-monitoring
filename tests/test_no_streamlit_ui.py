from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NoStreamlitUiTest(unittest.TestCase):
    def test_streamlit_ui_files_are_removed(self) -> None:
        removed_files = [
            "app/streamlit_app.py",
            "app/dashboard_chat.py",
            "app/dashboard_components.py",
            "app/dashboard_data.py",
            "app/dashboard_styles.py",
            "app/rag_pipeline.py",
            "tests/test_dashboard_recent_query.py",
            "tests/test_streamlit_dashboard_helpers.py",
        ]

        for relative_path in removed_files:
            with self.subTest(path=relative_path):
                self.assertFalse((ROOT / relative_path).exists())

    def test_streamlit_is_not_a_runtime_dependency(self) -> None:
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()

        self.assertNotIn("streamlit", {line.strip().lower() for line in requirements})


if __name__ == "__main__":
    unittest.main()
