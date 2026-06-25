"""Extractor Agent: parses raw contract text into structured Clause objects."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime

from app.models.schemas import Clause, AgentStep
from app.models.state import ContractState

logger = logging.getLogger(__name__)

CLAUSE_TYPES = [
    "termination", "liability", "non_compete", "arbitration",
    "warranty", "indemnification", "auto_renewal", "habitability",
    "payment", "confidentiality", "other"
]

EXTRACTION_PROMPT = """You are a legal document parser specializing in contract clause extraction.

Given the following contract text, extract ALL substantive clauses. For each clause:
1. Assign a sequential ID in format "C-001", "C-002", etc.
2. Classify the clause type from: {clause_types}
3. Capture the exact original text of the clause
4. Note approximate line range (start_line, end_line) as integers
5. Write a one-sentence plain-language summary

Return ONLY a valid JSON array with this exact structure (no markdown, no preamble):
[
  {{
    "clause_id": "C-001",
    "clause_type": "payment",
    "original_text": "Tenant agrees to pay $2,500 per month...",
    "line_range": [15, 18],
    "summary": "Tenant must pay $2,500 monthly rent with a $200 late fee after the 5th."
  }}
]

Contract type: {contract_type}
Contract text:
{contract_text}"""


def run_extractor_agent(state: ContractState, llm) -> dict:
    """Extract clauses from contract text using the LLM."""
    logger.info("[Extractor] Starting clause extraction for session %s", state["session_id"])

    step_start = AgentStep(
        step_name="Extractor Agent",
        step_number=1,
        status="running",
        output_summary="Parsing contract into structured clauses...",
        timestamp=datetime.utcnow(),
    )

    try:
        prompt = EXTRACTION_PROMPT.format(
            clause_types=", ".join(CLAUSE_TYPES),
            contract_type=state["contract_type"],
            contract_text=state["contract_text"][:8000],  # Safety truncation
        )

        response = llm.invoke(prompt)
        raw_text = response.content if hasattr(response, "content") else str(response)

        # Strip markdown code fences if present
        raw_text = re.sub(r"```(?:json)?", "", raw_text).strip()

        clauses_data = json.loads(raw_text)
        clauses = []

        for item in clauses_data:
            # Normalize line_range
            lr = item.get("line_range", [1, 1])
            if isinstance(lr, list) and len(lr) == 2:
                line_range = (int(lr[0]), int(lr[1]))
            else:
                line_range = (1, 1)

            # Ensure clause_id is in correct format
            clause_id = item.get("clause_id", f"C-{len(clauses)+1:03d}")
            if not re.match(r"^C-\d+$", clause_id):
                clause_id = f"C-{len(clauses)+1:03d}"

            clauses.append(Clause(
                clause_id=clause_id,
                clause_type=item.get("clause_type", "other"),
                original_text=item.get("original_text", ""),
                line_range=line_range,
                summary=item.get("summary", ""),
            ))

        step_done = AgentStep(
            step_name="Extractor Agent",
            step_number=1,
            status="completed",
            output_summary=f"Extracted {len(clauses)} clauses from contract.",
            timestamp=datetime.utcnow(),
        )

        logger.info("[Extractor] Extracted %d clauses", len(clauses))

        return {
            "clauses": clauses,
            "current_step": "evaluator",
            "chain_log": [step_start, step_done],
        }

    except json.JSONDecodeError as exc:
        logger.error("[Extractor] JSON parse error: %s", exc)
        # Fallback: extract using heuristic
        clauses = _heuristic_extract(state["contract_text"])

        step_done = AgentStep(
            step_name="Extractor Agent",
            step_number=1,
            status="completed",
            output_summary=f"Extracted {len(clauses)} clauses (heuristic fallback).",
            timestamp=datetime.utcnow(),
        )

        return {
            "clauses": clauses,
            "current_step": "evaluator",
            "chain_log": [step_start, step_done],
        }

    except Exception as exc:
        logger.error("[Extractor] Unexpected error: %s", exc)
        step_failed = AgentStep(
            step_name="Extractor Agent",
            step_number=1,
            status="failed",
            output_summary=f"Extraction failed: {exc}",
            timestamp=datetime.utcnow(),
        )
        return {
            "clauses": [],
            "current_step": "error",
            "error_message": str(exc),
            "chain_log": [step_start, step_failed],
        }


def _heuristic_extract(contract_text: str) -> list[Clause]:
    """Simple heuristic extractor as fallback."""
    clauses = []
    lines = contract_text.split("\n")
    current_clause_lines = []
    current_start = 0
    clause_counter = 1

    section_pattern = re.compile(r"^\s*(\d+)\.\s+([A-Z][A-Z\s/]+)", re.MULTILINE)

    matches = list(section_pattern.finditer(contract_text))
    for i, match in enumerate(matches):
        start_pos = match.start()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(contract_text)

        clause_text = contract_text[start_pos:end_pos].strip()
        title = match.group(2).strip().lower()

        # Map title to clause type
        clause_type = "other"
        type_map = {
            "non-compete": "non_compete", "non compete": "non_compete",
            "arbitration": "arbitration", "liability": "liability",
            "habitability": "habitability", "payment": "payment", "rent": "payment",
            "termination": "termination", "confidentiality": "confidentiality",
            "warranty": "warranty", "indemnif": "indemnification",
            "auto_renewal": "auto_renewal", "renewal": "auto_renewal",
        }
        for key, val in type_map.items():
            if key in title:
                clause_type = val
                break

        # Count lines
        start_line = contract_text[:start_pos].count("\n") + 1
        end_line = contract_text[:end_pos].count("\n") + 1

        clauses.append(Clause(
            clause_id=f"C-{clause_counter:03d}",
            clause_type=clause_type,
            original_text=clause_text[:1000],
            line_range=(start_line, end_line),
            summary=f"Section: {match.group(2).strip()}",
        ))
        clause_counter += 1

    return clauses
