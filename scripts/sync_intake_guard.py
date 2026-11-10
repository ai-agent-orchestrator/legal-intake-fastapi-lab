"""Copy canonical cores byte-for-byte into the installable mirror. Never rewrite app/."""
import argparse
import ast
from hashlib import sha256
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FILES = ("policy_core.py", "marketing_core.py")


def package_version(root=ROOT):
    tree = ast.parse((Path(root) / "app/security/policy_core.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "MASKING_VERSION" for t in node.targets):
            match = re.fullmatch(r"legal-pii-(\d{4})-(\d{2})-(\d{2})-v(\d+)", ast.literal_eval(node.value))
            if match:
                return ".".join(str(int(part)) for part in match.groups())
    raise ValueError("unsupported MASKING_VERSION; review package version mapping")


def sync(root=ROOT, check=False):
    root = Path(root)
    destination = root / "packages/intake_guard/src/intake_guard"
    mismatches = []
    for name in FILES:
        source = root / "app/security" / name
        target = destination / name
        raw = source.read_bytes()
        if not target.exists() or sha256(target.read_bytes()).digest() != sha256(raw).digest():
            mismatches.append(name)
            if not check:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
    project = root / "packages/intake_guard/pyproject.toml"
    text = project.read_text(encoding="utf-8")
    expected = package_version(root)
    if re.search(r'^version\s*=\s*"' + re.escape(expected) + r'"\s*$', text, re.M) is None:
        mismatches.append("package version")
        if not check:
            project.write_text(re.sub(r'^version\s*=\s*"[^"]+"', f'version = "{expected}"', text, count=1, flags=re.M), encoding="utf-8")
    return mismatches


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    changed = sync(check=args.check)
    print(("mismatch: " if args.check else "synced: ") + (", ".join(changed) or "already identical"))
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
