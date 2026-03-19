from backend.tests.test_backend_config import get_client


def test_frontend_root_serves_minimal_shell():
    client = get_client()
    response = client.get("/")

    assert response.status_code == 200
    assert "Minimal transcription" in response.text
    assert "Use this tab for local media already on disk" not in response.text


def test_docs_and_assets_remain_available():
    client = get_client()

    docs_response = client.get("/docs")
    assert docs_response.status_code == 200

    asset_response = client.get("/assets/app.js")
    assert asset_response.status_code == 200
    assert "init()" in asset_response.text
