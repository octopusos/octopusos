"""Schema output parser with deterministic extraction and strict validation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Optional

import jsonschema


@dataclass
class ParseError:
    """Structured parse error for audit and repair workflows."""

    stage: str
    message: str
    strategy: Optional[str] = None
    path: str = ""
    validator: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None


@dataclass
class JsonCandidate:
    """Extracted JSON candidate with deterministic strategy metadata."""

    text: str
    strategy: str


@dataclass
class ParseResult:
    """Schema parse result that is JSON-serializable for run_tape/audit."""

    ok: bool
    data: Any = None
    errors: list[ParseError] = field(default_factory=list)
    raw_excerpt: str = ""
    json_candidate: Optional[str] = None
    schema_id: str = "inline"
    schema_hash: str = ""
    parse_strategy: Optional[str] = None
    candidate_index: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["errors"] = [asdict(error) for error in self.errors]
        return payload


class SchemaOutputParser:
    """Deterministic output parser for schema-constrained JSON."""

    def __init__(
        self,
        schema_resolver: Optional[Callable[[str], dict[str, Any]]] = None,
        max_excerpt_chars: int = 800,
        max_candidate_chars: int = 20000,
        max_candidates: int = 3,
    ):
        self.schema_resolver = schema_resolver
        self.max_excerpt_chars = max_excerpt_chars
        self.max_candidate_chars = max_candidate_chars
        self.max_candidates = max_candidates

    def parse(self, schema: dict[str, Any] | str, raw_text: str) -> ParseResult:
        schema_dict, schema_id = self._resolve_schema(schema)
        schema_hash = self._schema_hash(schema_dict)
        raw_excerpt = self._truncate(raw_text)

        candidates = self.extract_json_candidates(raw_text)
        if not candidates:
            return ParseResult(
                ok=False,
                errors=[
                    ParseError(
                        stage="extract",
                        message="No JSON candidate found in output",
                    )
                ],
                raw_excerpt=raw_excerpt,
                schema_id=schema_id,
                schema_hash=schema_hash,
            )

        parse_errors: list[ParseError] = []
        for idx, candidate in enumerate(candidates):
            candidate_text = candidate.text[: self.max_candidate_chars]
            try:
                data = json.loads(candidate_text)
            except json.JSONDecodeError as exc:
                parse_errors.append(
                    ParseError(
                        stage="parse",
                        strategy=candidate.strategy,
                        message=exc.msg,
                        line=exc.lineno,
                        column=exc.colno,
                    )
                )
                continue

            validator = jsonschema.Draft202012Validator(schema_dict)
            validation_errors = list(validator.iter_errors(data))
            if not validation_errors:
                return ParseResult(
                    ok=True,
                    data=data,
                    errors=[],
                    raw_excerpt=raw_excerpt,
                    json_candidate=self._truncate(candidate_text),
                    schema_id=schema_id,
                    schema_hash=schema_hash,
                    parse_strategy=candidate.strategy,
                    candidate_index=idx,
                )

            validation_structured: list[ParseError] = []
            for error in validation_errors[:20]:
                path = "/" + "/".join(str(part) for part in error.absolute_path)
                validation_structured.append(
                    ParseError(
                        stage="validate",
                        strategy=candidate.strategy,
                        path=path if path != "/" else "",
                        message=error.message,
                        validator=error.validator,
                    )
                )

            return ParseResult(
                ok=False,
                errors=validation_structured,
                raw_excerpt=raw_excerpt,
                json_candidate=self._truncate(candidate_text),
                schema_id=schema_id,
                schema_hash=schema_hash,
                parse_strategy=candidate.strategy,
                candidate_index=idx,
            )

        return ParseResult(
            ok=False,
            errors=parse_errors,
            raw_excerpt=raw_excerpt,
            schema_id=schema_id,
            schema_hash=schema_hash,
        )

    def extract_json_candidates(self, raw_text: str) -> list[JsonCandidate]:
        candidates: list[JsonCandidate] = []

        # Strategy 1: fenced code blocks
        for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", raw_text, flags=re.IGNORECASE):
            block = match.group(1).strip()
            if block and self._looks_like_json(block):
                candidates.append(JsonCandidate(text=block, strategy="code_fence"))

        # Strategy 2: first balanced object/array segment
        first_segment = self._find_first_balanced_segment(raw_text)
        if first_segment:
            candidates.append(JsonCandidate(text=first_segment, strategy="first_balanced"))

        # Strategy 3: longest balanced object/array segment
        longest = self._find_longest_balanced_segment(raw_text)
        if longest:
            candidates.append(JsonCandidate(text=longest, strategy="longest_balanced"))

        deduped: list[JsonCandidate] = []
        seen: set[str] = set()
        for candidate in candidates:
            normalized = candidate.text.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(JsonCandidate(text=normalized, strategy=candidate.strategy))
            if len(deduped) >= self.max_candidates:
                break

        return deduped

    def _resolve_schema(self, schema: dict[str, Any] | str) -> tuple[dict[str, Any], str]:
        if isinstance(schema, dict):
            schema_id = str(schema.get("$id") or schema.get("title") or "inline")
            return schema, schema_id

        if self.schema_resolver is None:
            raise ValueError(f"schema resolver is required for schema_id '{schema}'")

        resolved = self.schema_resolver(schema)
        return resolved, schema

    def _schema_hash(self, schema: dict[str, Any]) -> str:
        canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _truncate(self, text: str, limit: Optional[int] = None) -> str:
        max_chars = limit if limit is not None else self.max_excerpt_chars
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "...(truncated)"

    def _looks_like_json(self, text: str) -> bool:
        stripped = text.strip()
        return (
            (stripped.startswith("{") and stripped.endswith("}"))
            or (stripped.startswith("[") and stripped.endswith("]"))
        )

    def _find_first_balanced_segment(self, text: str) -> Optional[str]:
        for idx, char in enumerate(text):
            if char in "[{":
                segment = self._extract_balanced_from(text, idx)
                if segment:
                    return segment
        return None

    def _find_longest_balanced_segment(self, text: str) -> Optional[str]:
        longest: Optional[str] = None
        for idx, char in enumerate(text):
            if char in "[{":
                segment = self._extract_balanced_from(text, idx)
                if segment and (longest is None or len(segment) > len(longest)):
                    longest = segment
        return longest

    def _extract_balanced_from(self, text: str, start: int) -> Optional[str]:
        opening = text[start]
        closing = "}" if opening == "{" else "]"
        depth = 0
        in_string = False
        escaped = False

        for idx in range(start, len(text)):
            ch = text[idx]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
                continue

            if ch == opening:
                depth += 1
            elif ch == closing:
                depth -= 1
                if depth == 0:
                    segment = text[start : idx + 1].strip()
                    if len(segment) <= self.max_candidate_chars and self._looks_like_json(segment):
                        return segment
                    return None

        return None
