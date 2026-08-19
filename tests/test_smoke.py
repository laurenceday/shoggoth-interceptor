import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class SmokeTest(unittest.TestCase):
    def test_shoggoth_imports_and_paths_resolve_inside_repo(self):
        spec = importlib.util.spec_from_file_location("shoggoth", REPO / "bin" / "shoggoth.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for path in (mod.STATE, mod.BOARD, mod.EXCLUDED, mod.PIPELINES):
            self.assertTrue(path.resolve().is_relative_to(REPO), path)


if __name__ == "__main__":
    unittest.main()
