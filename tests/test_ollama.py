from unittest.mock import MagicMock, patch

import httpx

from roop.adapters.model import ChatMessage
from roop.adapters.ollama import OllamaClient, TransientOllamaError


def test_chat_requests_json_format():
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client

    response = MagicMock()
    response.json.return_value = {
        "message": {"content": '{"files": []}'},
        "done": True,
    }
    mock_client.post.return_value = response

    with patch("roop.adapters.ollama.httpx.Client", return_value=mock_client):
        result = OllamaClient().chat([
            ChatMessage(role="system", content="Return JSON"),
            ChatMessage(role="user", content="Make a patch"),
        ])

    request_body = mock_client.post.call_args.kwargs["json"]
    assert request_body["format"] == "json"
    assert request_body["options"]["temperature"] == 0.1
    assert request_body["options"]["repeat_penalty"] == 1.15
    assert request_body["options"]["repeat_last_n"] == 128
    assert request_body["options"]["num_predict"] == 8192
    assert request_body["options"]["num_ctx"] == 8192
    assert result.content == '{"files": []}'
    assert result.done is True


def test_set_temperature_is_sent_to_ollama() -> None:
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    response = MagicMock()
    response.json.return_value = {"message": {"content": "{}"}, "done": True}
    mock_client.post.return_value = response
    with patch("roop.adapters.ollama.httpx.Client", return_value=mock_client):
        client = OllamaClient()
        client.set_temperature(0.4)
        client.chat([ChatMessage(role="user", content="hi")])
    request_body = mock_client.post.call_args.kwargs["json"]
    assert request_body["options"]["temperature"] == 0.4


def test_transient_500_retries_then_succeeds_without_surfacing() -> None:
    sleeps: list[float] = []
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    failed = MagicMock()
    failed.status_code = 500
    failed.text = "overloaded"
    ok = MagicMock()
    ok.status_code = 200
    ok.json.return_value = {"message": {"content": "{\"ok\": true}"}, "done": True}
    mock_client.post.side_effect = [failed, ok]

    with patch("roop.adapters.ollama.httpx.Client", return_value=mock_client):
        result = OllamaClient(sleeper=sleeps.append).chat([
            ChatMessage(role="user", content="hi"),
        ])

    assert result.content == "{\"ok\": true}"
    assert sleeps == [0.5]
    assert mock_client.post.call_count == 2


def test_repeated_500_raises_after_backoff() -> None:
    sleeps: list[float] = []
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    failed = MagicMock()
    failed.status_code = 500
    failed.text = "overloaded"
    mock_client.post.return_value = failed

    with patch("roop.adapters.ollama.httpx.Client", return_value=mock_client):
        try:
            OllamaClient(sleeper=sleeps.append).chat([
                ChatMessage(role="user", content="hi"),
            ])
            raised = False
        except TransientOllamaError:
            raised = True

    assert raised is True
    assert len(sleeps) == 3
    assert mock_client.post.call_count == 4


def test_connect_error_is_transient() -> None:
    sleeps: list[float] = []
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    request = httpx.Request("POST", "http://127.0.0.1:11434/api/chat")
    mock_client.post.side_effect = httpx.ConnectError("down", request=request)

    with patch("roop.adapters.ollama.httpx.Client", return_value=mock_client):
        try:
            OllamaClient(sleeper=sleeps.append).chat([
                ChatMessage(role="user", content="hi"),
            ])
            raised = False
        except TransientOllamaError:
            raised = True

    assert raised is True
    assert len(sleeps) == 3
