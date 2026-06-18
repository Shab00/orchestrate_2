from __future__ import annotations

import os
from pathlib import Path

import typer
from dotenv import load_dotenv
from openai import OpenAI
from rich import print

from agent.agent import OpenAIToolAgent
from agent.tools import build_default_registry
from prompts.system import SYSTEM_PROMPT
from retrieval.retriever import HybridRetriever

app = typer.Typer(help="Hackathon AI agent scaffold")


@app.command()
def run(
    query: str = typer.Argument(..., help="User request for the agent."),
    knowledge_dir: Path = typer.Option(Path("knowledge"), help="Folder containing markdown files."),
    model: str = typer.Option("gpt-4.1-mini", help="OpenAI model name."),
) -> None:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise typer.BadParameter("OPENAI_API_KEY is required.")
    retriever = HybridRetriever.from_markdown_folder(knowledge_dir)
    registry = build_default_registry(retriever)
    agent = OpenAIToolAgent(OpenAI(api_key=api_key), model, SYSTEM_PROMPT, registry)
    response = agent.run(query)
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    app()
