"""PR-style patch export for generated tests."""

from __future__ import annotations

import difflib
from pathlib import Path

from generator import GeneratedSuite


def make_pr_patch(suite: GeneratedSuite) -> str:
    """Return a unified diff that adds the generated tests and a CI hint."""
    sections: list[str] = []
    for relative, content in sorted(suite.files.items()):
        new_lines = content.splitlines(keepends=True)
        diff = difflib.unified_diff(
            [],
            new_lines,
            fromfile="/dev/null",
            tofile=f"b/{relative}",
            lineterm="",
        )
        sections.append("\n".join(diff))

    ci_hint = "pytest tests -q\n"
    sections.append(
        "\n".join(
            difflib.unified_diff(
                [],
                [ci_hint],
                fromfile="/dev/null",
                tofile="b/TESTFORGE_CI_HINT.txt",
                lineterm="",
            )
        )
    )
    return "\n\n".join(sections) + "\n"


def write_patch(suite: GeneratedSuite, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(make_pr_patch(suite), encoding="utf-8")
    return output

