from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ApiImageDependencyTest(unittest.TestCase):
    def test_api_image_installs_cpu_torch_before_sentence_transformers(self) -> None:
        dockerfile = (ROOT / "Dockerfile.api").read_text(encoding="utf-8")
        requirements = (ROOT / "requirements-api.txt").read_text(encoding="utf-8")

        self.assertIn("https://download.pytorch.org/whl/cpu", dockerfile)
        self.assertIn("torch", dockerfile)
        self.assertIn("EMBEDDING_MODEL=intfloat/multilingual-e5-base", dockerfile)
        self.assertIn("SentenceTransformer(os.environ['EMBEDDING_MODEL'])", dockerfile)
        self.assertIn("sentence-transformers", requirements)
        self.assertLess(
            dockerfile.index("https://download.pytorch.org/whl/cpu"),
            dockerfile.index("pip install -r requirements-api.txt"),
        )
        self.assertLess(
            dockerfile.index("pip install -r requirements-api.txt"),
            dockerfile.index("SentenceTransformer(os.environ['EMBEDDING_MODEL'])"),
        )


if __name__ == "__main__":
    unittest.main()
