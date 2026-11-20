from streamlit.testing.v1 import AppTest


def test_app_loads_in_public_mode() -> None:
    app = AppTest.from_file("../app.py", default_timeout=10).run()
    assert not app.exception
    assert any(title.value == "Van Lam" for title in app.title)
    assert any(header.value == "Ask about this portfolio" for header in app.header)
    assert [button.label for button in app.button[:4]] == [
        "Public",
        "Signed in",
        "Selected visitor",
        "Owner",
    ]
