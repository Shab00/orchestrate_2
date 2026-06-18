from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, TypedDict

if TYPE_CHECKING:
    from retrieval.retriever import HybridRetriever


class ToolResult(TypedDict):
    ok: bool
    content: str
    metadata: dict[str, str]


ToolHandler = Callable[[dict[str, Any]], ToolResult]


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, tool: ToolSpec) -> None:
        self._tools[tool.name] = tool

    def openai_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.input_schema,
                },
            }
            for spec in self._tools.values()
        ]

    def dispatch(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        spec = self._tools.get(name)
        if not spec:
            return {"ok": False, "content": f"Unknown tool: {name}", "metadata": {"tool": name}}
        return spec.handler(arguments)


def build_default_registry(retriever: "HybridRetriever") -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="search_markdown",
            description="Search markdown knowledge files with hybrid retrieval.",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "minimum": 1, "maximum": 10}},
                "required": ["query"],
            },
            handler=lambda args: _search_markdown(args, retriever),
        )
    )
    return registry


def _search_markdown(arguments: dict[str, Any], retriever: "HybridRetriever") -> ToolResult:
    query = str(arguments.get("query", "")).strip()
    top_k = int(arguments.get("top_k", 5))
    if not query:
        return {"ok": False, "content": "query is required", "metadata": {"tool": "search_markdown"}}
    hits = retriever.query(query_text=query, top_k=top_k)
    lines = [f"{idx + 1}. {hit['source']} (score={hit['score']:.3f})" for idx, hit in enumerate(hits)]
    content = "\n".join(lines) if lines else "No retrieval hits found."
    return {"ok": True, "content": content, "metadata": {"tool": "search_markdown"}}
