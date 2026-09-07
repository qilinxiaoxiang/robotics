#!/usr/bin/env python3
"""Validate the machine-readable research map without external dependencies."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
VALID_EVIDENCE = {f"E{level}" for level in range(6)}
VALID_LAYERS = {
    "world-model",
    "robot-intelligence",
    "open-platform",
    "deployment-platform",
    "robot-body",
    "vertical-robot",
    "autonomous-science",
}
# These environments keep independent histories; their dependencies are not research-map documents.
SKIP_TOP_LEVEL = {"berkeley-deeprl-homework-spring2026", "ethz-course-2026", "microduck-sim"}


def load_json(name: str) -> dict:
    with (RESEARCH / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_local_links(errors: list[str]) -> int:
    link_pattern = re.compile(r"\[[^]]+\]\(([^)]+)\)")
    checked = 0
    for markdown in ROOT.rglob("*.md"):
        relative_parts = markdown.relative_to(ROOT).parts
        if (
            any(part.startswith(".") for part in relative_parts)
            or relative_parts[0] in SKIP_TOP_LEVEL
        ):
            continue
        text = markdown.read_text(encoding="utf-8")
        for raw_target in link_pattern.findall(text):
            target = raw_target.split("#", 1)[0]
            if not target or urlparse(target).scheme or target.startswith("mailto:"):
                continue
            checked += 1
            resolved = (markdown.parent / target).resolve()
            require(resolved.exists(), f"Broken local link in {markdown}: {raw_target}", errors)
    return checked


def main() -> int:
    errors: list[str] = []
    problems_doc = load_json("problems.json")
    companies_doc = load_json("companies.json")

    require(problems_doc["as_of"] == companies_doc["as_of"], "as_of dates differ", errors)
    as_of = date.fromisoformat(companies_doc["as_of"])
    require(as_of <= date.today(), "research map is dated in the future", errors)

    problems = problems_doc["problems"]
    problem_ids = [problem["id"] for problem in problems]
    require(len(problem_ids) == len(set(problem_ids)), "duplicate problem ID", errors)
    require(set(problem_ids) == {f"P{i}" for i in range(8)}, "problem IDs must be P0 through P7", errors)

    companies = companies_doc["companies"]
    company_ids = [company["id"] for company in companies]
    require(len(company_ids) == len(set(company_ids)), "duplicate company ID", errors)
    require(len(companies) >= 10, "company roster is too small for an L2 landscape", errors)

    for company in companies:
        prefix = company.get("id", "<missing-id>")
        require(company.get("layer") in VALID_LAYERS, f"{prefix}: invalid layer", errors)
        require(
            company.get("evidence_level") in VALID_EVIDENCE,
            f"{prefix}: invalid evidence level",
            errors,
        )
        require(bool(company.get("problems")), f"{prefix}: missing problem links", errors)
        for problem_id in company.get("problems", []):
            require(problem_id in problem_ids, f"{prefix}: unknown problem {problem_id}", errors)
        source = urlparse(company.get("source", ""))
        require(source.scheme == "https" and bool(source.netloc), f"{prefix}: invalid source URL", errors)
        verified = date.fromisoformat(company["last_verified"])
        require(verified <= as_of, f"{prefix}: verified after map as_of date", errors)

    links_checked = validate_local_links(errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        f"OK: {len(companies)} organizations, {len(problems)} problems, "
        f"{links_checked} local links; map as of {as_of.isoformat()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
