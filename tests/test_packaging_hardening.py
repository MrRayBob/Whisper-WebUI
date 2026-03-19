from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_requirements_split():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    legacy_requirements = (ROOT / "requirements-legacy.txt").read_text(encoding="utf-8")

    assert "--extra-index-url" not in requirements
    assert "jhj0517-whisper" not in requirements
    assert "scipy" in requirements
    assert legacy_requirements.strip() == (
        "git+https://github.com/jhj0517/jhj0517-whisper.git@197244318d5d75d9d195bff0705ab05a591684ec"
    )


def test_install_script_uses_python3_and_bootstrap():
    install_script = (ROOT / "Install.sh").read_text(encoding="utf-8")

    assert "python3 -m venv venv" in install_script
    assert "python3 -m pip install -U pip \"setuptools<82\" wheel" in install_script
    assert "--no-build-isolation -r requirements-legacy.txt" in install_script


def test_dockerfiles_support_torch_extra_index_url():
    root_dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    backend_dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")

    assert "ARG TORCH_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cu128" in root_dockerfile
    assert "python3 -m pip install -r requirements.txt --extra-index-url \"$TORCH_EXTRA_INDEX_URL\"" in root_dockerfile
    assert "--no-build-isolation -r requirements-legacy.txt" in root_dockerfile

    assert "ARG TORCH_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cu128" in backend_dockerfile
    assert "python3 -m pip install -r backend/requirements-backend.txt --extra-index-url \"$TORCH_EXTRA_INDEX_URL\"" in backend_dockerfile
    assert "--no-build-isolation -r requirements-legacy.txt" in backend_dockerfile
