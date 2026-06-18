from typing import Any

from agent.schemas import AgentResponse, coerce_structured_output
from agent.tools import ToolRegistry, ToolSpec


def _echo_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "content": str(arguments.get("value", "")), "metadata": {"tool": "echo"}}


def test_coerce_structured_output_validates_schema() -> None:
    response = coerce_structured_output(
        '{"action":"triage","justification":"clear","evidence":["doc"],"confidence":0.7}'
    )
    assert isinstance(response, AgentResponse)
    assert response.action == "triage"


def test_tool_registry_dispatches_tool() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="echo",
            description="Echo back a value.",
            input_schema={"type": "object", "properties": {"value": {"type": "string"}}},
            handler=_echo_tool,
        )
    )
    result = registry.dispatch("echo", {"value": "hello"})
    assert result["ok"] is True
    assert result["content"] == "hello"
