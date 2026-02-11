"""Lightweight AnswerPack TUI entrypoint.

This provides a minimal interactive flow for creating AnswerPacks when
`--ui tui` is requested. If Textual is unavailable, it falls back to
terminal prompts while keeping the same output behavior.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from rich.console import Console

from octopusos.core.answers import AnswerStore, validate_answer_pack
from octopusos.core.time import utc_now_iso

console = Console()


def _maybe_get_llm_suggestions(
    question_pack: Dict[str, Any],
    llm: bool,
    llm_provider: str,
) -> Optional[List[Dict[str, Any]]]:
    if not llm:
        return None
    try:
        from octopusos.core.answers.llm_suggester import suggest_all_answers

        suggestions, errors = suggest_all_answers(
            question_pack=question_pack,
            provider=llm_provider,
            fallback_provider="anthropic" if llm_provider == "openai" else "openai",
        )
        if errors:
            console.print("[yellow]Some suggestions failed:[/yellow]")
            for error in errors:
                console.print(f"  - {error}")
        return suggestions
    except Exception as exc:
        console.print(f"[yellow]Warning: LLM suggestions failed: {exc}[/yellow]")
        console.print("[yellow]Continuing without suggestions...[/yellow]")
        return None


def run_answer_tui(
    question_pack_path: str,
    output_path: str,
    llm: bool = False,
    llm_provider: str = "openai",
) -> Path:
    """Run a minimal interactive TUI flow to create an AnswerPack."""
    question_pack_file = Path(question_pack_path)
    with question_pack_file.open("r", encoding="utf-8") as handle:
        question_pack = json.load(handle)

    console.print(f"[cyan]Loaded QuestionPack: {question_pack.get('pack_id')}[/cyan]")
    console.print(f"Questions: {len(question_pack.get('questions', []))}\n")

    llm_suggestions = _maybe_get_llm_suggestions(question_pack, llm, llm_provider)
    suggestions_by_qid: Dict[str, List[Dict[str, Any]]] = {}
    if llm_suggestions:
        for sugg in llm_suggestions:
            suggestions_by_qid.setdefault(sugg.get("question_id"), []).append(sugg)

    store = AnswerStore()
    answer_pack_id = store.generate_pack_id(question_pack.get("pack_id"))

    answers: List[Dict[str, Any]] = []
    questions = question_pack.get("questions", [])
    for i, question in enumerate(questions, 1):
        console.print(f"\n[bold]Question {i}/{len(questions)}[/bold]")
        console.print(f"ID: {question.get('question_id')}")
        console.print(f"Type: {question.get('type')} (Blocking: {question.get('blocking_level')})")
        console.print(f"\n{question.get('question_text')}\n")
        console.print(f"[dim]Context: {question.get('context')}[/dim]\n")

        suggested = question.get("suggested_answers", [])
        if not suggested:
            suggested = suggestions_by_qid.get(question.get("question_id"), [])

        if suggested:
            console.print("[cyan]Suggested answers:[/cyan]")
            for j, sugg in enumerate(suggested, 1):
                console.print(f"  {j}. {sugg.get('answer_text')}")
                if sugg.get("rationale"):
                    console.print(f"     [dim]{sugg.get('rationale')}[/dim]")
            console.print()

        answer_text = click.prompt("Your answer", type=str)
        evidence_refs = click.prompt(
            "Evidence references (comma-separated)",
            type=str,
            default="user_input",
        ).split(",")
        evidence_refs = [ref.strip() for ref in evidence_refs if ref.strip()]

        answers.append(
            {
                "question_id": question.get("question_id"),
                "answer_type": "text",
                "answer_text": answer_text,
                "evidence_refs": evidence_refs if evidence_refs else ["user_input"],
                "provided_at": utc_now_iso(),
                "provided_by": "human",
                "rationale": "Provided by user via TUI",
            }
        )

    answer_pack = {
        "answer_pack_id": answer_pack_id,
        "schema_version": "0.11.0",
        "question_pack_id": question_pack.get("pack_id"),
        "intent_id": question_pack.get("intent_id"),
        "answers": answers,
        "provided_at": utc_now_iso(),
        "completeness": {
            "total_questions": len(questions),
            "answered": len(answers),
            "unanswered_question_ids": [],
            "fallback_used": False,
        },
        "lineage": {
            "nl_request_id": question_pack.get("intent_id", "unknown"),
            "pipeline_run_id": str(question_pack_file.parent.parent),
            "created_by": "octopusos-tui",
            "created_at": utc_now_iso(),
        },
    }

    answer_pack["checksum"] = store.compute_checksum(answer_pack)

    console.print("\n[cyan]Validating AnswerPack...[/cyan]")
    valid, errors = validate_answer_pack(answer_pack, question_pack)
    if not valid:
        console.print("[red]Validation failed:[/red]")
        for error in errors:
            console.print(f"  - {error}")
        raise click.Abort()

    output_file = store.save(answer_pack, Path(output_path))
    console.print(f"\n[green]✓ AnswerPack created: {output_file}[/green]")
    console.print(f"  ID: {answer_pack_id}")
    console.print(f"  Answers: {len(answers)}")
    return output_file

