from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
import typer
from dotenv import load_dotenv
from openai import OpenAI
from rich import print

from agent.agent import OpenAIToolAgent
from agent.claim_agent import process_claim
from agent.tools import build_default_registry
from data.loader import load_claims, load_evidence_requirements, load_user_history
from prompts.system import SYSTEM_PROMPT
from retrieval.retriever import HybridRetriever

app = typer.Typer(help="Damage claim verification agent + hackathon scaffold")

OUTPUT_COLUMNS = [
    "user_id", "image_paths", "user_claim", "claim_object",
    "evidence_standard_met", "evidence_standard_met_reason",
    "risk_flags", "issue_type", "object_part", "claim_status",
    "claim_status_justification", "supporting_image_ids",
    "valid_image", "severity",
]


@app.command()
def claims(
    claims_csv: Path = typer.Option(Path("claims/claims.csv"), help="Path to claims CSV."),
    user_history_csv: Path = typer.Option(Path("claims/user_history.csv"), help="Path to user history CSV."),
    evidence_csv: Path = typer.Option(Path("claims/evidence_requirements.csv"), help="Path to evidence requirements CSV."),
    output_csv: Path = typer.Option(Path("output.csv"), help="Path to write output CSV."),
    sleep: float = typer.Option(1.5, help="Seconds to sleep between API calls."),
) -> None:
    """Process all claims and write structured verdicts to output.csv."""
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise typer.BadParameter("OPENAI_API_KEY is required. Set it with: export OPENAI_API_KEY=sk-...")

    claim_rows = load_claims(claims_csv)
    user_history = load_user_history(user_history_csv)
    evidence_requirements = load_evidence_requirements(evidence_csv)
    total = len(claim_rows)
    results = []

    print(f"[bold]Processing {total} claims...[/bold]")
    for i, row in enumerate(claim_rows, start=1):
        uid = row.get("user_id", "")
        print(f"  [{i}/{total}] user_id: {uid}")
        history = user_history.get(uid, {})
        verdict = process_claim(row, history, evidence_requirements)
        results.append(verdict.to_csv_row(row))
        if i < total:
            time.sleep(sleep)

    pd.DataFrame(results, columns=OUTPUT_COLUMNS).to_csv(output_csv, index=False)
    print(f"\n[green]Done.[/green] {total} claims written to {output_csv}")


@app.command()
def run(
    query: str = typer.Argument(..., help="User request for the agent."),
    knowledge_dir: Path = typer.Option(Path("knowledge"), help="Folder containing markdown files."),
    model: str = typer.Option("gpt-4.1-mini", help="OpenAI model name."),
) -> None:
    """Run the generic hackathon AI agent on a query."""
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
