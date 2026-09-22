#!/usr/bin/env python3
"""Validate the deterministic CEA-Extended construction fixture.

This checks one symbolic toy example. It does not validate natural-language
oracles in general and reports no model performance.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


FIXTURE = Path(__file__).with_name("extended_fixture.json")
REQUIRED_FAMILIES = {
    "baseline",
    "counterfactual",
    "nuisance",
    "ablation",
    "redundancy",
    "conflict",
}
ROUTE = re.compile(r"^Courier Vela routes through ([A-Za-z]+)\.$")
SEAL = re.compile(r"^([A-Za-z]+) uses the ([A-Za-z]+) seal\.$")
REGISTRY = re.compile(
    r"^The ([A-Za-z]+) registry independently lists the ([A-Za-z]+) seal\.$"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def doc_map(condition: dict) -> dict[str, str]:
    documents = condition["documents"]
    ids = [document["id"] for document in documents]
    require(len(ids) == len(set(ids)), f"{condition['id']}: duplicate document ID")
    return {document["id"]: document["text"] for document in documents}


def toy_oracle(condition: dict) -> tuple[str | None, set[frozenset[str]]]:
    """Derive this fixture's answer/proofs from its controlled claim grammar."""
    documents = doc_map(condition)
    routes: list[tuple[str, str]] = []
    seals: list[tuple[str, str, str]] = []
    for document_id, text in documents.items():
        if match := ROUTE.fullmatch(text):
            routes.append((document_id, match.group(1)))
        elif match := SEAL.fullmatch(text):
            seals.append((document_id, match.group(1), match.group(2)))
        elif match := REGISTRY.fullmatch(text):
            seals.append((document_id, match.group(1), match.group(2)))
    if condition["family"] == "conflict":
        require(len({depot for _, depot in routes}) > 1, "conflict must be real")
        policy = condition["resolution_policy"]
        require(policy in {"authority", "abstain"}, "unknown conflict policy")
        if policy == "abstain":
            return None, set()
        authority_ids = set(condition["authority_document_ids"])
        routes = [route for route in routes if route[0] in authority_ids]
    if len({depot for _, depot in routes}) != 1:
        return None, set()
    proofs_by_answer: dict[str, set[frozenset[str]]] = {}
    for route_id, route_depot in routes:
        for seal_id, seal_depot, answer in seals:
            if seal_depot == route_depot:
                proofs_by_answer.setdefault(answer, set()).add(
                    frozenset({route_id, seal_id})
                )
    if len(proofs_by_answer) != 1:
        return None, set()
    answer = next(iter(proofs_by_answer))
    return answer, proofs_by_answer[answer]


def validate_case(case: dict) -> None:
    require(case["id"] == "vela-seal", "unexpected worked-case ID")
    require(case["question"] == "Which seal is assigned to courier Vela?", "question drift")
    conditions = case["conditions"]
    ids = [condition["id"] for condition in conditions]
    require(len(ids) == len(set(ids)), "duplicate condition ID")
    families = Counter(condition["family"] for condition in conditions)
    require(set(families) == REQUIRED_FAMILIES, "incomplete or unknown role matrix")
    require(families["baseline"] == 1, "expected exactly one baseline")
    require(families["counterfactual"] >= 2, "need multiple decisive edits")
    require(all(families[family] >= 1 for family in REQUIRED_FAMILIES - {"baseline", "counterfactual"}), "missing extension role")
    baseline = next(c for c in conditions if c["family"] == "baseline")
    require(baseline["id"] == "baseline", "baseline condition ID drift")
    base_docs = doc_map(baseline)
    base_answer = baseline["expected_answer"]
    base_proofs = {frozenset(proof) for proof in baseline["proof_sets"]}
    require(len(base_proofs) >= 2, "fixture requires alternative base proofs")

    counterfactual_answers: set[str] = set()
    for condition in conditions:
        condition_id = condition["id"]
        documents = doc_map(condition)
        document_ids = set(documents)
        removed = set(condition["removed_document_ids"])
        changed = set(condition["changed_document_ids"])
        require(document_ids <= set(base_docs), f"{condition_id}: added document ID")
        require(removed == set(base_docs) - document_ids, f"{condition_id}: removal metadata mismatch")
        require(
            changed == {
                document_id
                for document_id in document_ids
                if documents[document_id] != base_docs[document_id]
            },
            f"{condition_id}: changed-document metadata mismatch",
        )
        require(not (changed & removed), f"{condition_id}: changed and removed overlap")
        require(bool(condition["rationale"].strip()), f"{condition_id}: missing rationale")
        answer, proofs = toy_oracle(condition)
        declared = [frozenset(proof) for proof in condition["proof_sets"]]
        require(len(declared) == len(set(declared)), f"{condition_id}: duplicate proof")
        require(all(proof and proof <= document_ids for proof in declared), f"{condition_id}: invalid proof IDs")
        require(
            not any(left < right for left in declared for right in declared),
            f"{condition_id}: non-minimal proof family",
        )
        require(answer == condition["expected_answer"], f"{condition_id}: oracle answer mismatch")
        require(set(declared) == proofs, f"{condition_id}: oracle proof mismatch")
        require((answer is None) == (not declared), f"{condition_id}: abstention/proof mismatch")

        family = condition["family"]
        if family == "counterfactual":
            require(changed and not removed, f"{condition_id}: invalid decisive edit")
            require(answer != base_answer, f"{condition_id}: answer did not change")
            counterfactual_answers.add(answer)
        elif family == "nuisance":
            require(not changed and not removed, f"{condition_id}: nuisance changed a claim")
            require([d["id"] for d in condition["documents"]] != list(base_docs), "nuisance did not reorder")
            require(answer == base_answer and proofs == base_proofs, "nuisance changed the oracle")
        elif family == "ablation":
            require(answer is None and removed, "necessity ablation must be insufficient")
            require(all(proof & removed for proof in base_proofs), "ablation left a base proof")
        elif family == "redundancy":
            require(answer == base_answer and removed, "redundancy must retain answer")
            require(any(proof <= document_ids for proof in base_proofs), "no alternate proof survives")
        elif family == "conflict":
            require(changed and not removed, "conflict must edit an existing document")
            policy = condition["resolution_policy"]
            require(policy in {"authority", "abstain"}, "fixture conflict policy drift")
            if policy == "authority":
                authority_ids = set(condition["authority_document_ids"])
                require(authority_ids <= document_ids, "missing authority document")
                require(any(proof & authority_ids for proof in proofs), "authority absent from proofs")
            else:
                require(answer is None and not proofs, "unresolved conflict must abstain")
    require(len(counterfactual_answers) >= 2, "counterfactuals should yield distinct answers")
    require(
        {c["resolution_policy"] for c in conditions if c["family"] == "conflict"}
        == {"authority", "abstain"},
        "fixture must exercise both conflict policies",
    )

    def citation_scores(condition: dict, citations: set[str]) -> tuple[bool, bool]:
        present = set(doc_map(condition))
        proofs = [set(proof) for proof in condition["proof_sets"]]
        coverage = citations <= present and any(proof <= citations for proof in proofs)
        exact = any(citations == proof for proof in proofs)
        return coverage, exact

    require(citation_scores(baseline, {"D1", "D2"}) == (True, True), "minimal proof should pass")
    require(citation_scores(baseline, {"D1", "D3"}) == (True, True), "alternative proof should pass")
    require(citation_scores(baseline, {"D1", "D2", "D3"}) == (True, False), "citation padding should fail exact")
    require(citation_scores(baseline, {"D1"}) == (False, False), "partial proof should fail")
    redundancy = next(c for c in conditions if c["family"] == "redundancy")
    require(citation_scores(redundancy, {"D1", "D3"}) == (True, True), "surviving proof should pass")
    require(citation_scores(redundancy, {"D1", "D2"}) == (False, False), "removed ID should fail")


def main() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    require(fixture["schema_version"] == 2, "expected dataset schema v2")
    require(len(fixture["cases"]) == 1, "expected one construction fixture")
    validate_case(fixture["cases"][0])

    # A finite transcript can be mimicked by a system that fails off-transcript.
    tested = {"baseline", "route-bramblecross", "route-cedarholm"}
    hidden = "unseen-valid-world"
    good = lambda world: "oracle-answer"
    bad = lambda world: "oracle-answer" if world in tested else "unsupported-guess"
    require(all(good(world) == bad(world) for world in tested), "transcript mismatch")
    require(good(hidden) != bad(hidden), "finite-audit counterexample failed")
    print("Validated CEA-Extended construction fixture and finite-audit counterexample.")


if __name__ == "__main__":
    main()
