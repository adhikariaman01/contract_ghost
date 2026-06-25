"""Loads unenforceability rules from JSON and seeds ChromaDB."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from app.models.schemas import EnforceabilityRule

logger = logging.getLogger(__name__)

RULES_FILE = Path(__file__).parent.parent / "data" / "legal_rules" / "unenforceability_rules.json"


def load_rules() -> list[EnforceabilityRule]:
    """Load all rules from JSON file."""
    if not RULES_FILE.exists():
        logger.warning("Rules file not found at %s", RULES_FILE)
        return []

    with open(RULES_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    rules = [EnforceabilityRule(**item) for item in raw]
    logger.info("Loaded %d enforceability rules", len(rules))
    return rules


def filter_rules(
    rules: list[EnforceabilityRule],
    jurisdiction: str,
    clause_type: str | None = None,
) -> list[EnforceabilityRule]:
    """Filter rules by jurisdiction and optional clause type."""
    filtered = [r for r in rules if r.jurisdiction == jurisdiction]
    if clause_type:
        filtered = [r for r in filtered if r.clause_type == clause_type]
    return filtered
