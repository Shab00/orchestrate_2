from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from agent.safety import run_safety_gates
from agent.schemas import AgentResponse, coerce_structured_output
from agent.tools import ToolRegistry


class OpenAIToolAgent:
    def __init__(
        self,
        client: OpenAI,
        model: str,
        system_prompt: str,
        tools: ToolRegistry,
        max_rounds: int = 3,
    ) -> None:
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools
        self.max_rounds = max_rounds

    def run(self, user_input: str) -> AgentResponse:
        safety = run_safety_gates(user_input)
        if not safety["passed"]:
            raise ValueError("; ".join(safety["reasons"]))
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input},
        ]
        for _ in range(self.max_rounds):
            completion = self._chat(messages)
            message = completion.choices[0].message
            tool_calls = message.tool_calls or []
            if not tool_calls:
                return coerce_structured_output(message.content or "{}")
            messages.append(message.model_dump(exclude_none=True))
            self._append_tool_results(messages, tool_calls)
        raise RuntimeError(
            f"Exceeded max tool-calling rounds ({self.max_rounds}) without final answer. "
            "Consider simplifying the query or increasing max_rounds."
        )

    def _chat(self, messages: list[dict[str, Any]]) -> Any:
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tools.openai_tools(),
            tool_choice="auto",
        )

    def _append_tool_results(self, messages: list[dict[str, Any]], tool_calls: list[Any]) -> None:
        for call in tool_calls:
            arguments = _parse_tool_args(call.function.arguments)
            result = self.tools.dispatch(call.function.name, arguments)
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)}
            )


def _parse_tool_args(raw_args: str | None) -> dict[str, Any]:
    if not raw_args:
        return {}
    try:
        parsed = json.loads(raw_args)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
