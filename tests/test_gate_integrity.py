import importlib.util
import shutil
import stat
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "bin" / "verify-gate.py"


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_gate", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class GateIntegrityTest(unittest.TestCase):
    def setUp(self):
        self.verifier = load_verifier()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        protected = {
            *self.verifier.PROTECTED_EXECUTABLES,
            *self.verifier.REQUIRED_SNIPPETS,
        }
        for relative in protected:
            source = REPO / relative
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def tearDown(self):
        self.tmp.cleanup()

    def test_repository_gate_surfaces_are_intact(self):
        self.assertEqual(self.verifier.verify(REPO), [])

    def test_changed_gate_is_rejected(self):
        gate = self.root / Path("bin/wildcat-gate.sh")
        gate.write_text(gate.read_text() + "\n# changed\n")
        self.assertIn(
            "protected digest does not match the pinned value: bin/wildcat-gate.sh",
            self.verifier.verify(self.root),
        )

    def test_changed_installer_is_rejected(self):
        installer = self.root / Path("bin/install-guardrails.sh")
        installer.write_text(installer.read_text() + "\n# changed\n")
        self.assertIn(
            "protected digest does not match the pinned value: bin/install-guardrails.sh",
            self.verifier.verify(self.root),
        )

    def test_missing_reference_is_rejected(self):
        readme = self.root / "README.md"
        readme.write_text(readme.read_text().replace("`bin/wildcat-gate.sh`", "gate"))
        self.assertTrue(
            any("required gate reference missing" in error for error in self.verifier.verify(self.root))
        )

    def test_non_executable_gate_is_rejected(self):
        gate = self.root / Path("bin/wildcat-gate.sh")
        gate.chmod(gate.stat().st_mode & ~stat.S_IXUSR)
        self.assertIn(
            "protected file is not executable: bin/wildcat-gate.sh",
            self.verifier.verify(self.root),
        )

    def test_non_executable_installer_is_rejected(self):
        installer = self.root / Path("bin/install-guardrails.sh")
        installer.chmod(installer.stat().st_mode & ~stat.S_IXUSR)
        self.assertIn(
            "protected file is not executable: bin/install-guardrails.sh",
            self.verifier.verify(self.root),
        )

    def test_symlinked_gate_is_rejected(self):
        gate = self.root / Path("bin/wildcat-gate.sh")
        gate.unlink()
        gate.symlink_to(REPO / "bin" / "wildcat-gate.sh")
        self.assertIn(
            "protected file is not regular: bin/wildcat-gate.sh",
            self.verifier.verify(self.root),
        )


if __name__ == "__main__":
    unittest.main()
