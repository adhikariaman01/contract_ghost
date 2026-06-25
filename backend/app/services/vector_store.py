"""ChromaDB vector store for enforceability rules retrieval."""
from __future__ import annotations

import json
import logging
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.models.schemas import EnforceabilityRule
from app.services.rules_loader import load_rules

logger = logging.getLogger(__name__)

_client: Optional[chromadb.Client] = None
_collection = None
_rules_cache: list[EnforceabilityRule] = []


def _get_client():
    global _client
    if _client is None:
        _client = chromadb.Client(ChromaSettings(anonymized_telemetry=False))
    return _client


def initialize_vector_store() -> None:
    """Load rules and seed the ChromaDB collection at startup."""
    global _collection, _rules_cache

    client = _get_client()

    # Reset collection
    try:
        client.delete_collection("legal_rules")
    except Exception:
        pass

    _collection = client.create_collection(
        name="legal_rules",
        metadata={"hnsw:space": "cosine"},
    )

    rules = load_rules()
    _rules_cache = rules

    if not rules:
        logger.warning("No rules loaded — vector store is empty")
        return

    documents = []
    metadatas = []
    ids = []

    for rule in rules:
        # Build a rich text representation for embedding
        doc_text = (
            f"Jurisdiction: {rule.jurisdiction}. "
            f"Clause type: {rule.clause_type}. "
            f"Rule: {rule.rule_text}"
        )
        if rule.statute_reference:
            doc_text += f" Statute: {rule.statute_reference}."
        if rule.case_law_reference:
            doc_text += f" Case: {rule.case_law_reference}."

        documents.append(doc_text)
        metadatas.append({
            "rule_id": rule.rule_id,
            "jurisdiction": rule.jurisdiction,
            "clause_type": rule.clause_type,
            "enforceability": rule.enforceability,
            "rule_json": json.dumps(rule.model_dump()),
        })
        ids.append(rule.rule_id)

    _collection.add(documents=documents, metadatas=metadatas, ids=ids)
    logger.info("Seeded vector store with %d rules", len(rules))


def retrieve_rules(
    jurisdiction: str,
    clause_type: str,
    clause_text: str,
    k: int = 3,
) -> list[EnforceabilityRule]:
    """Retrieve top-k relevant rules for a given clause."""
    if _collection is None:
        logger.error("Vector store not initialized")
        return []

    query = f"Jurisdiction: {jurisdiction}. Clause type: {clause_type}. {clause_text}"

    try:
        results = _collection.query(
            query_texts=[query],
            n_results=min(k, len(_rules_cache)),
            where={"jurisdiction": jurisdiction},
        )

        rules: list[EnforceabilityRule] = []
        if results and results["metadatas"]:
            for meta in results["metadatas"][0]:
                rule_data = json.loads(meta["rule_json"])
                rules.append(EnforceabilityRule(**rule_data))

        return rules

    except Exception as exc:
        logger.error("Vector store query failed: %s", exc)
        # Fallback: simple in-memory filter
        return [r for r in _rules_cache
                if r.jurisdiction == jurisdiction and r.clause_type == clause_type][:k]
