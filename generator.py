"""Deterministic capture-then-assert test generation."""

from __future__ import annotations

import importlib
import itertools
import reprlib
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from analyzer import Analysis, FunctionInfo


@dataclass(frozen=True)
class CapturedCase:
    """One executed behavior captured from the current code."""

    args: tuple[Any, ...]
    outcome: str
    value_repr: str | None = None
    exception_type: str | None = None


@dataclass(frozen=True)
class GeneratedSuite:
    """Rendered tests and source capture metadata."""

    files: dict[str, str]
    cases_by_function: dict[str, list[CapturedCase]]
    assertion_count: int


def generate_suite(analysis: Analysis, max_cases_per_function: int = 4) -> GeneratedSuite:
    """Generate a green characterization suite by executing current behavior."""
    _ensure_import_root(analysis.root.parent)
    files: dict[str, str] = {}
    cases_by_function: dict[str, list[CapturedCase]] = {}
    for fn in analysis.functions:
        candidates = deterministic_inputs(fn, max_cases=max_cases_per_function)
        cases = capture(fn, candidates)
        if not cases:
            continue
        cases_by_function[f"{fn.module}.{fn.qualname}"] = cases
        file_name = f"tests/test_{_safe_name(fn.module)}_{_safe_name(fn.qualname)}.py"
        files[file_name] = render_test_file(fn, cases)

    assertion_count = sum(len(cases) for cases in cases_by_function.values())
    return GeneratedSuite(files=files, cases_by_function=cases_by_function, assertion_count=assertion_count)


def deterministic_inputs(fn: FunctionInfo, max_cases: int = 4) -> list[tuple[Any, ...]]:
    """Infer a compact set of inputs from type hints and parameter names."""
    if fn.arity == 0:
        return [()]

    choices = [_values_for_parameter(name, fn.type_hints.get(name, "")) for name in fn.parameters]
    cases = list(itertools.islice(itertools.product(*choices), max_cases))
    return [tuple(case) for case in cases]


def capture(fn: FunctionInfo, cases: list[tuple[Any, ...]]) -> list[CapturedCase]:
    """Execute a function on candidate inputs and record output or exception."""
    callable_obj = _load_callable(fn)
    captured: list[CapturedCase] = []
    for args in cases:
        if len(args) != fn.arity:
            continue
        try:
            value = callable_obj(*args)
        except Exception as exc:  # noqa: BLE001 - exceptions are the behavior being captured.
            captured.append(
                CapturedCase(args=args, outcome="exception", exception_type=type(exc).__name__)
            )
        else:
            captured.append(CapturedCase(args=args, outcome="return", value_repr=_literal(value)))
    return captured


def render_test_file(fn: FunctionInfo, cases: list[CapturedCase]) -> str:
    """Render a pytest module for captured behavior."""
    needs_pytest = any(case.outcome == "exception" for case in cases)
    imports = ["from datetime import date"]
    if needs_pytest:
        imports.append("import pytest")
    imports.append(f"from {fn.module} import {fn.import_name}")

    body: list[str] = []
    for index, case in enumerate(cases, start=1):
        test_name = f"test_{_safe_name(fn.qualname)}_case_{index}"
        body.append("")
        body.append(f"def {test_name}():")
        args = ", ".join(_literal(arg) for arg in case.args)
        if case.outcome == "exception":
            body.append(f"    with pytest.raises({case.exception_type}):")
            body.append(f"        {fn.import_name}({args})")
        else:
            body.append(f"    assert {fn.import_name}({args}) == {case.value_repr}")

    return "\n".join(imports + body) + "\n"


def write_suite(suite: GeneratedSuite, target_dir: str | Path) -> Path:
    """Write generated test files under target_dir and return that path."""
    root = Path(target_dir)
    for relative, content in suite.files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def _ensure_import_root(path: Path) -> None:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


def _load_callable(fn: FunctionInfo):
    module = importlib.import_module(fn.module)
    obj = module
    for part in fn.qualname.split("."):
        obj = getattr(obj, part)
    return obj


def _values_for_parameter(name: str, hint: str) -> list[Any]:
    hint = hint.replace("typing.", "")
    lower_name = name.lower()
    if hint in {"int"}:
        if lower_name in {"qty", "quantity"}:
            return [1, 10, 0, -1]
        if lower_name in {"n", "limit", "length"}:
            return [5, 3, 0, -1]
        return [0, 1, -1, 2]
    if hint in {"float"}:
        if lower_name in {"pct", "rate"}:
            return [10.0, 0.0, 100.0, -1.0]
        return [100.0, 0.0, 12.5, -2.0]
    if hint in {"str"}:
        return ["Hello, World!", "  Already clean  ", "", "A/B test"]
    if hint in {"bool"}:
        return [True, False]
    if hint in {"date", "datetime.date"}:
        return [date(2026, 6, 15), date(2026, 6, 14), date(2024, 2, 29)]
    if hint.startswith("list"):
        if "tuple" in hint or lower_name == "lines":
            return [[(2, 10.0), (1, 5.5)], [], [(0, 99.0)]]
        return [[], [1], [1, 2, 3]]
    return [1, "x", 0]


def _literal(value: Any) -> str:
    if isinstance(value, date):
        return f"date({value.year}, {value.month}, {value.day})"
    text = repr(value)
    if len(text) > 120:
        return reprlib.repr(value)
    return text


def _safe_name(name: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in name).strip("_").lower()

