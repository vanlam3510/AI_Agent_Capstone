from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.llm_agent import answer_visitor_question, draft_project_update
from core.models import PortfolioItem


def make_client(response_text: str) -> MagicMock:
    client = MagicMock()
    client.__enter__.return_value = client
    client.models.generate_content.return_value = SimpleNamespace(text=response_text)
    return client


def test_visitor_question_keeps_client_open_for_request() -> None:
    client = make_client("Van builds AI systems.")
    items = [PortfolioItem(id="1", category="about", title="Skills", content="AI systems")]

    with patch("core.llm_agent.get_client", return_value=client):
        answer = answer_visitor_question("What are Van's skills?", items)

    assert answer == "Van builds AI systems."
    client.__enter__.assert_called_once_with()
    client.models.generate_content.assert_called_once()
    client.__exit__.assert_called_once()


def test_owner_draft_keeps_client_open_for_request() -> None:
    client = make_client("Project draft")

    with patch("core.llm_agent.get_client", return_value=client):
        answer = draft_project_update("Built a secure agent.")

    assert answer == "Project draft"
    client.__enter__.assert_called_once_with()
    client.models.generate_content.assert_called_once()
    client.__exit__.assert_called_once()
