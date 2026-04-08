#!/usr/bin/env python3
import importlib.util
import json
import os
import sys
from pathlib import Path


def _check_file(path: Path):
    return path.exists() and path.is_file()


def _validate_reset_endpoint(repo_root: Path):
    inference_path = repo_root / "inference.py"
    if not inference_path.exists():
        return False, "inference.py missing"

    spec = importlib.util.spec_from_file_location("inference", inference_path)
    if spec is None or spec.loader is None:
        return False, "could not load inference.py"

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    app = getattr(module, "app", None)
    if app is None:
        return False, "inference.py does not expose app"

    with app.test_client() as client:
        response = client.post("/reset")
        if response.status_code != 200:
            return False, f"POST /reset returned {response.status_code}"

        if response.is_json:
            payload = response.get_json(silent=True) or {}
            if not isinstance(payload, dict):
                return False, "POST /reset did not return a JSON object"
        else:
            return False, "POST /reset did not return JSON"

    return True, "POST /reset OK"


def run_validate(repo_root: Path):
    checks = []

    dockerfile_ok = _check_file(repo_root / "Dockerfile")
    checks.append(("Dockerfile at repo root", dockerfile_ok, "present" if dockerfile_ok else "missing"))

    inference_ok = _check_file(repo_root / "inference.py")
    checks.append(("inference.py at repo root", inference_ok, "present" if inference_ok else "missing"))

    openenv_ok = _check_file(repo_root / "openenv.yaml")
    checks.append(("openenv.yaml at repo root", openenv_ok, "present" if openenv_ok else "missing"))

    reset_ok, reset_msg = _validate_reset_endpoint(repo_root)
    checks.append(("OpenEnv Reset (POST OK)", reset_ok, reset_msg))

    failed = [c for c in checks if not c[1]]

    print("OpenEnv Validation")
    print("==================")
    for name, ok, msg in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {msg}")

    if failed:
        print("\nValidation failed.")
        return 1

    print("\nValidation passed.")
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] not in {"validate"}:
        print("Usage: openenv validate", file=sys.stderr)
        return 2

    repo_root = Path(os.getcwd())
    return run_validate(repo_root)


if __name__ == "__main__":
    raise SystemExit(main())
