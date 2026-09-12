#!/usr/bin/env python3
"""Validate local manuscript references and publication links."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_URL = "https://github.com/sergiofigueras/causal-evidence-audit"
RELEASE_URL = f"{REPOSITORY_URL}/releases/tag/v0.1.0"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    manuscript = (ROOT / "main.tex").read_text(encoding="utf-8")
    bibliography = (ROOT / "references.bib").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")

    citation_groups = re.findall(r"\\cite[tp]\{([^}]+)\}", manuscript)
    used_keys = {
        key.strip()
        for group in citation_groups
        for key in group.split(",")
        if key.strip()
    }
    bibliography_keys = set(
        re.findall(r"^@\w+\{([^,]+),", bibliography, flags=re.MULTILINE)
    )
    require(
        used_keys == bibliography_keys,
        f"citation mismatch: missing={sorted(used_keys - bibliography_keys)}, "
        f"unused={sorted(bibliography_keys - used_keys)}",
    )
    for path, text in (
        ("main.tex", manuscript),
        ("README.md", readme),
        ("CITATION.cff", citation),
    ):
        require(REPOSITORY_URL in text, f"repository URL missing from {path}")
        require(RELEASE_URL in text, f"release URL missing from {path}")
    require((ROOT / "LICENSE").is_file(), "LICENSE is missing")
    require((ROOT / "main.pdf").stat().st_size > 100_000, "main.pdf is missing or too small")
    print(
        f"Validated {len(used_keys)} citation keys, publication URLs, license, "
        "and compiled-paper presence."
    )


if __name__ == "__main__":
    main()
