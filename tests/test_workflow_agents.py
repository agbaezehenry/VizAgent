"""Simple unit tests for workflow agents."""

import unittest
from unittest.mock import patch, MagicMock
from plotly_agent.workflow_agents import (
    CommunicationAgent,
    ChartRouter,
    BaseAgent,
)


class TestChartRouter(unittest.TestCase):
    """Test chart type routing."""

    def test_routes_line_chart(self):
        result = ChartRouter.route("line")
        self.assertEqual(result, "line")

    def test_routes_unknown_to_scatter(self):
        result = ChartRouter.route("unknown")
        self.assertEqual(result, "scatter")

    def test_routes_case_insensitive(self):
        result = ChartRouter.route("BAR")
        self.assertEqual(result, "bar")


class TestCommunicationAgentParsing(unittest.TestCase):
    """Test response parsing logic."""

    @patch.object(BaseAgent, "__init__", lambda self, model: None)
    def test_parse_ready_action(self):
        agent = CommunicationAgent.__new__(CommunicationAgent)
        agent.prompt_template = ""

        response = "<action>ready</action><story_summary>Show sales over time</story_summary>"
        result = agent._parse_response(response)

        self.assertEqual(result["action"], "ready")
        self.assertEqual(result["story_summary"], "Show sales over time")

    @patch.object(BaseAgent, "__init__", lambda self, model: None)
    def test_parse_clarify_action(self):
        agent = CommunicationAgent.__new__(CommunicationAgent)
        agent.prompt_template = ""

        response = "<action>clarify</action><question>What time range?</question>"
        result = agent._parse_response(response)

        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["message"], "What time range?")


class TestBaseAgentLLMCall(unittest.TestCase):
    """Test LLM call parameter handling."""

    @patch("plotly_agent.workflow_agents.OpenAI")
    def test_call_llm_without_temperature(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="test response"))
        ]

        agent = BaseAgent(model="test-model")
        agent.call_llm([{"role": "user", "content": "hello"}])

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertNotIn("temperature", call_kwargs)

    @patch("plotly_agent.workflow_agents.OpenAI")
    def test_call_llm_with_temperature(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="test response"))
        ]

        agent = BaseAgent(model="test-model")
        agent.call_llm([{"role": "user", "content": "hello"}], temperature=0.5)

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_kwargs["temperature"], 0.5)


if __name__ == "__main__":
    unittest.main()
