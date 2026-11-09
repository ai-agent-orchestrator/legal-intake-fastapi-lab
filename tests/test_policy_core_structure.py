"""P0/O4: enforce file-level independence before any install-package extraction."""
import ast
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", ["policy_core", "marketing_core"])
def test_core_only_imports_standard_library(name):
    path = ROOT / "app/security" / (name + ".py")
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0
            assert node.module.split(".")[0] in sys.stdlib_module_names
        elif isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] in sys.stdlib_module_names for alias in node.names)


@pytest.mark.parametrize("name,expression,expected", [
    ("policy_core", "mask_personal_data('synthetic@example.invalid').safe_text", "[EMAIL]"),
    ("marketing_core", "check_marketing_response('무조건 승소합니다.').decision.value", "REVIEW"),
])
def test_core_file_imports_with_site_packages_and_app_unavailable(tmp_path, name, expression, expected):
    # Copy only this file; isolated Python cannot import the surrounding app or site packages.
    target = tmp_path / (name + ".py")
    target.write_bytes((ROOT / "app/security" / (name + ".py")).read_bytes())
    code = "import runpy,sys; scope=runpy.run_path(sys.argv[1]); print(eval(sys.argv[2], scope))"
    result = subprocess.run([sys.executable, "-I", "-S", "-c", code, str(target), expression],
                            capture_output=True, text=True, encoding="utf-8", timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected
