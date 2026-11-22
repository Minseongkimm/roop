from unittest.mock import MagicMock, patch

from roop.adapters.model import ChatMessage
from roop.adapters.ollama import OllamaClient


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
    assert result.content == '{"files": []}'
    assert result.done is True
