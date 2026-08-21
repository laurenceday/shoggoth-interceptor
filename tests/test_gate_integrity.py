import importlib.util
import shutil
import stat
import subprocess
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
        gate = self.root / Path("bin/repository-gate.py")
        gate.write_text(gate.read_text() + "\n# changed\n")
        self.assertIn(
            "protected digest does not match the pinned value: bin/repository-gate.py",
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
        readme.write_text(readme.read_text().replace("`bin/repository-gate.py`", "gate"))
        self.assertTrue(
            any("required gate reference missing" in error for error in self.verifier.verify(self.root))
        )

    def test_non_executable_gate_is_rejected(self):
        gate = self.root / Path("bin/repository-gate.py")
        gate.chmod(gate.stat().st_mode & ~stat.S_IXUSR)
        self.assertIn(
            "protected file is not executable: bin/repository-gate.py",
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
        gate = self.root / Path("bin/repository-gate.py")
        gate.unlink()
        gate.symlink_to(REPO / "bin" / "repository-gate.py")
        self.assertIn(
            "protected file is not regular: bin/repository-gate.py",
            self.verifier.verify(self.root),
        )


if __name__ == "__main__":
    unittest.main()


class GeneratedHookTest(unittest.TestCase):
    """The installed hook must abort when the integrity check fails.

    Nothing covered this before: the hook ran verify-gate.py on its own line
    with no `set -e` and no check of its status, so a digest mismatch printed a
    warning and the push proceeded into the very gate the pin had just failed.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        fake_bin = self.root / "fake-root" / "bin"
        fake_bin.mkdir(parents=True)
        shutil.copy2(REPO / "bin" / "install-guardrails.sh", fake_bin / "install-guardrails.sh")
        self.marker = self.root / "gate-ran"
        self.verifier = fake_bin / "verify-gate.py"
        self.gate = fake_bin / "repository-gate.py"
        self.gate.write_text(
            "#!/bin/sh\n" f'printf %s reached > "{self.marker}"\n' "exit 0\n"
        )
        for script in (fake_bin / "install-guardrails.sh", self.gate):
            script.chmod(script.stat().st_mode | stat.S_IXUSR)
        self.clone = self.root / "clone"
        self.clone.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.clone, check=True)
        self.installer = fake_bin / "install-guardrails.sh"

    def tearDown(self):
        self.tmp.cleanup()

    def _install_and_push(self, verifier_exit):
        self.verifier.write_text(f"#!/bin/sh\necho 'gate integrity: tampered' >&2\nexit {verifier_exit}\n")
        self.verifier.chmod(self.verifier.stat().st_mode | stat.S_IXUSR)
        subprocess.run(
            [str(self.installer), str(self.clone)],
            check=True,
            capture_output=True,
            text=True,
        )
        hook = self.clone / ".git" / "hooks" / "pre-push"
        self.assertTrue(hook.exists())
        return subprocess.run(
            [str(hook), "origin", "https://github.com/example/example.git"],
            capture_output=True,
            text=True,
        )

    def test_failing_integrity_check_blocks_the_push(self):
        result = self._install_and_push(verifier_exit=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(
            self.marker.exists(),
            "the gate ran even though the integrity check failed",
        )

    def test_passing_integrity_check_reaches_the_gate(self):
        result = self._install_and_push(verifier_exit=0)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.marker.exists())
