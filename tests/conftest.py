import pytest


@pytest.fixture
def text_payload() -> dict[str, str]:
    return {"text": "You are an awful and disgusting idiot."}
