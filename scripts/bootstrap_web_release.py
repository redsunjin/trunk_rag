from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


class BootstrapError(RuntimeError):
    pass


def venv_python_path(root_dir: Path) -> Path:
    if sys.platform == "win32":
        return root_dir / ".venv" / "Scripts" / "python.exe"
    return root_dir / ".venv" / "bin" / "python"


def run_command(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )


def ensure_env_file(root_dir: Path) -> dict[str, object]:
    env_path = root_dir / ".env"
    example_path = root_dir / ".env.example"
    if env_path.exists():
        return {"created": False, "path": str(env_path)}
    if not example_path.exists():
        raise BootstrapError(".env.example not found.")
    shutil.copyfile(example_path, env_path)
    return {"created": True, "path": str(env_path)}


def ensure_virtualenv(root_dir: Path, bootstrap_python: str) -> dict[str, object]:
    target = venv_python_path(root_dir)
    if target.exists():
        return {"created": False, "python": str(target)}

    result = run_command([bootstrap_python, "-m", "venv", ".venv"], cwd=root_dir)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise BootstrapError(f"virtualenv creation failed: {detail}")

    return {"created": True, "python": str(target)}


def check_runtime_dependencies(root_dir: Path, python_exe: str) -> dict[str, object]:
    result = run_command(
        [python_exe, "-c", "import fastapi, uvicorn, chromadb"],
        cwd=root_dir,
    )
    return {
        "ready": result.returncode == 0,
        "detail": (result.stderr or result.stdout or "").strip(),
    }


def install_runtime_dependencies(root_dir: Path, python_exe: str) -> dict[str, object]:
    result = run_command(
        [python_exe, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=root_dir,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise BootstrapError(f"requirements install failed: {detail}")
    return {"installed": True}


def bootstrap_release_web(root_dir: Path, bootstrap_python: str) -> dict[str, object]:
    env_result = ensure_env_file(root_dir)
    venv_result = ensure_virtualenv(root_dir, bootstrap_python)
    runtime_python = str(venv_python_path(root_dir))

    dependency_check = check_runtime_dependencies(root_dir, runtime_python)
    installed_requirements = False
    if not dependency_check["ready"]:
        install_runtime_dependencies(root_dir, runtime_python)
        installed_requirements = True
        dependency_check = check_runtime_dependencies(root_dir, runtime_python)
        if not dependency_check["ready"]:
            detail = str(dependency_check.get("detail", "")).strip()
            raise BootstrapError(f"runtime import check still failing after install: {detail}")

    return {
        "env": env_result,
        "venv": venv_result,
        "requirements_installed": installed_requirements,
        "python": runtime_python,
    }


def print_report(report: dict[str, object]) -> None:
    env_result = dict(report["env"])
    venv_result = dict(report["venv"])
    print("[bootstrap-web-release] ready")
    print(f"  python={report['python']}")
    print(f"  env={'created' if env_result['created'] else 'existing'}:{env_result['path']}")
    print(f"  venv={'created' if venv_result['created'] else 'existing'}:{venv_result['python']}")
    print(f"  requirements_installed={report['requirements_installed']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap the single recommended web MVP install/start path."
    )
    parser.add_argument("--bootstrap-python", type=str, default=sys.executable)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = bootstrap_release_web(ROOT_DIR, args.bootstrap_python)
    except BootstrapError as exc:
        print(f"[bootstrap-web-release] failed: {exc}", file=sys.stderr)
        return 1

    print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
