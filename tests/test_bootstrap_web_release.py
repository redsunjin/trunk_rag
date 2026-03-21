from __future__ import annotations

from pathlib import Path

from scripts import bootstrap_web_release


def test_ensure_env_file_copies_example(tmp_path: Path):
    (tmp_path / ".env.example").write_text("LLM_PROVIDER=lmstudio\n", encoding="utf-8")

    result = bootstrap_web_release.ensure_env_file(tmp_path)

    assert result["created"] is True
    assert (tmp_path / ".env").read_text(encoding="utf-8") == "LLM_PROVIDER=lmstudio\n"


def test_ensure_virtualenv_skips_existing(tmp_path: Path):
    python_path = bootstrap_web_release.venv_python_path(tmp_path)
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")

    result = bootstrap_web_release.ensure_virtualenv(tmp_path, "python")

    assert result["created"] is False
    assert result["python"] == str(python_path)


def test_bootstrap_release_web_installs_requirements_when_import_probe_fails(
    tmp_path: Path,
    monkeypatch,
):
    (tmp_path / ".env.example").write_text("LLM_PROVIDER=lmstudio\n", encoding="utf-8")
    python_path = bootstrap_web_release.venv_python_path(tmp_path)
    python_path.parent.mkdir(parents=True, exist_ok=True)
    python_path.write_text("", encoding="utf-8")

    install_calls: list[list[str]] = []
    state = {"probe_calls": 0}

    def fake_run_command(args: list[str], *, cwd: Path):
        class Result:
            def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        if args[1:3] == ["-m", "venv"]:
            python_path.parent.mkdir(parents=True, exist_ok=True)
            python_path.write_text("", encoding="utf-8")
            return Result(0)
        if args[1:] == ["-c", "import fastapi, uvicorn, chromadb"]:
            state["probe_calls"] += 1
            return Result(1 if state["probe_calls"] == 1 else 0, stderr="missing")
        if args[1:4] == ["-m", "pip", "install"]:
            install_calls.append(args)
            return Result(0)
        return Result(0)

    monkeypatch.setattr(bootstrap_web_release, "run_command", fake_run_command)

    report = bootstrap_web_release.bootstrap_release_web(tmp_path, "python")

    assert report["requirements_installed"] is True
    assert install_calls


def test_bootstrap_release_web_creates_env_and_venv_without_install_when_ready(
    tmp_path: Path,
    monkeypatch,
):
    (tmp_path / ".env.example").write_text("LLM_PROVIDER=lmstudio\n", encoding="utf-8")
    python_path = bootstrap_web_release.venv_python_path(tmp_path)

    def fake_run_command(args: list[str], *, cwd: Path):
        class Result:
            def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        if args[1:3] == ["-m", "venv"]:
            python_path.parent.mkdir(parents=True, exist_ok=True)
            python_path.write_text("", encoding="utf-8")
            return Result(0)
        return Result(0)

    monkeypatch.setattr(bootstrap_web_release, "run_command", fake_run_command)

    report = bootstrap_web_release.bootstrap_release_web(tmp_path, "python")

    assert report["env"]["created"] is True
    assert report["venv"]["created"] is True
    assert report["requirements_installed"] is False
