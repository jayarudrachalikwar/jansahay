def test_application_imports() -> None:
    from app.main import app

    assert app.title == "JanSahay AI"
    assert app.version == "0.1.0"
