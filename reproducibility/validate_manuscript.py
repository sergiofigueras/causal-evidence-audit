#!/usr/bin/env python3
"""Validate local manuscript references and publication links."""

import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_URL = "https://github.com/sergiofigueras/causal-evidence-audit"
RELEASE_URL = f"{REPOSITORY_URL}/releases/tag/v0.1.0"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def citation_keys(manuscript):
    return [
        key.strip()
        for group in re.findall(r"\\cite[tp]\{([^}]+)\}", manuscript)
        for key in group.split(",")
        if key.strip()
    ]


def math_spans(manuscript):
    inline = re.findall(r"(?<!\\)\$(?!\$)(.*?)(?<!\\)\$", manuscript, re.DOTALL)
    displayed = [
        match.group(1)
        for match in re.finditer(
            r"\\begin\{(?:equation\*?|align\*?)\}(.*?)"
            r"\\end\{(?:equation\*?|align\*?)\}",
            manuscript,
            re.DOTALL,
        )
    ]
    return [re.sub(r"\s+", "", span) for span in inline + displayed]


def table_numbers(manuscript):
    tables = re.findall(
        r"\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}",
        manuscript,
        re.DOTALL,
    )
    return [
        [number.replace(",", ".") for number in re.findall(r"\d+(?:[.,]\d+)?", table)]
        for table in tables
    ]


def validate_translation(original, translation):
    require(
        Counter(citation_keys(original)) == Counter(citation_keys(translation)),
        "Portuguese manuscript citation occurrences differ from English",
    )
    for expression, description in (
        (r"\\(?:section|subsection)\*?\{", "section structure"),
        (r"\\begin\{(?:proposition|definition|proof|figure|table)\}", "formal/figure/table structure"),
    ):
        require(
            re.findall(expression, original) == re.findall(expression, translation),
            f"Portuguese manuscript {description} differs from English",
        )
    for expression, description in (
        (r"\\label\{([^}]+)\}", "labels"),
        (r"\\(?:[Cc]ref|ref|eqref)\{([^}]+)\}", "internal references"),
    ):
        require(
            re.findall(expression, original) == re.findall(expression, translation),
            f"Portuguese manuscript {description} differ from English",
        )
    require(
        Counter(math_spans(original)) == Counter(math_spans(translation)),
        "Portuguese manuscript mathematical expressions differ from English",
    )
    require(
        table_numbers(original) == table_numbers(translation),
        "Portuguese manuscript table values differ from English",
    )
    for version in (original, translation):
        require("CEA-Extended" in version, "CEA-Extended section missing")
        require("\\label{prop:finite}" in version, "finite-audit proposition missing")


def main():
    manuscript = (ROOT / "main.tex").read_text(encoding="utf-8")
    translated = (ROOT / "main_pt_br.tex").read_text(encoding="utf-8")
    bibliography = (ROOT / "references.bib").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_pt_br = (ROOT / "README.pt-BR.md").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")

    validate_translation(manuscript, translated)
    used_keys = set(citation_keys(manuscript))
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
        ("main_pt_br.tex", translated),
        ("README.md", readme),
        ("README.pt-BR.md", readme_pt_br),
        ("CITATION.cff", citation),
    ):
        require(REPOSITORY_URL in text, f"repository URL missing from {path}")
        require(RELEASE_URL in text, f"release URL missing from {path}")
    require((ROOT / "LICENSE").is_file(), "LICENSE is missing")
    require((ROOT / "main.pdf").stat().st_size > 100_000, "main.pdf is missing or too small")
    require(
        (ROOT / "main_pt_br.pdf").stat().st_size > 100_000,
        "main_pt_br.pdf is missing or too small",
    )
    print(
        f"Validated {len(used_keys)} citation keys, Portuguese/English parity, "
        "publication URLs, license, and compiled-paper presence."
    )


if __name__ == "__main__":
    main()
