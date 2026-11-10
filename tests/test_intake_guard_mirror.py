from hashlib import sha256
import importlib.metadata
from pathlib import Path
import tomllib

from scripts.sync_intake_guard import package_version, sync

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_and_mirror_bytes_are_identical():
    for name in ("policy_core.py", "marketing_core.py"):
        source = ROOT / "app/security" / name
        mirror = ROOT / "packages/intake_guard/src/intake_guard" / name
        assert sha256(source.read_bytes()).digest() == sha256(mirror.read_bytes()).digest()
    assert sync(check=True) == []


def test_masking_and_package_versions_are_synchronized():
    import intake_guard
    metadata = tomllib.loads((ROOT / "packages/intake_guard/pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["project"]["version"] == package_version() == intake_guard.__version__
    assert importlib.metadata.version("intake-guard") == intake_guard.__version__
