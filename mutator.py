"""Fast hand-rolled mutation scoring for the bundled legacy sample."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from generator import GeneratedSuite, write_suite
from runner import RunResult, run_pytest


@dataclass(frozen=True)
class Mutation:
    id: str
    file: str
    find: str
    replace: str
    label: str


@dataclass(frozen=True)
class MutationResult:
    mutation: Mutation
    killed: bool
    run: RunResult


@dataclass(frozen=True)
class MutationScore:
    killed: int
    total: int
    results: tuple[MutationResult, ...]

    @property
    def percent(self) -> float:
        return 0.0 if self.total == 0 else round(self.killed / self.total * 100, 1)

    @property
    def survived(self) -> list[Mutation]:
        return [result.mutation for result in self.results if not result.killed]

    def headline(self) -> str:
        return f"{self.killed}/{self.total} behavior changes detected"


MUTATIONS: tuple[Mutation, ...] = (
    Mutation(
        id="bulk_multiply_to_divide",
        file="pricing.py",
        find="return round(unit * qty * discount, 2)",
        replace="return round(unit / qty * discount, 2)",
        label="pricing.py bulk_price * -> /",
    ),
    Mutation(
        id="discount_minus_to_plus",
        file="pricing.py",
        find="return round(price * (1 - pct / 100), 2)",
        replace="return round(price * (1 + pct / 100), 2)",
        label="pricing.py apply_discount - -> +",
    ),
    Mutation(
        id="tax_plus_to_minus",
        file="pricing.py",
        find="return round(amount * (1 + rate / 100), 2)",
        replace="return round(amount * (1 - rate / 100), 2)",
        label="pricing.py with_tax + -> -",
    ),
    Mutation(
        id="line_multiply_to_plus",
        file="invoice.py",
        find="return round(qty * unit, 2)",
        replace="return round(qty + unit, 2)",
        label="invoice.py line_total * -> +",
    ),
    Mutation(
        id="weekend_ge_to_gt",
        file="dates.py",
        find="return d.weekday() >= 5",
        replace="return d.weekday() > 5",
        label="dates.py is_weekend >= -> >",
    ),
    Mutation(
        id="days_abs_removed",
        file="dates.py",
        find="return abs((b - a).days)",
        replace="return (b - a).days",
        label="dates.py days_between remove abs",
    ),
    Mutation(
        id="slug_strip_removed",
        file="slugify.py",
        find="return cleaned.strip(\"-\")",
        replace="return cleaned",
        label="slugify.py strip removed",
    ),
    Mutation(
        id="truncate_len_lt",
        file="slugify.py",
        find="if len(s) <= n:",
        replace="if len(s) < n:",
        label="slugify.py <= -> <",
    ),
    Mutation(
        id="bulk_return_none",
        file="pricing.py",
        find="return round(unit * qty * discount, 2)",
        replace="return None",
        label="pricing.py bulk_price return None",
    ),
)


def mutation_score(
    source_parent: str | Path,
    suite: GeneratedSuite,
    tmp_root: str | Path,
    package_name: str = "legacy_repo",
    mutations: tuple[Mutation, ...] = MUTATIONS,
) -> MutationScore:
    """Apply each mutation to a copy and run the generated suite."""
    source_parent = Path(source_parent).resolve()
    tmp_root = Path(tmp_root).resolve()
    tmp_root.mkdir(parents=True, exist_ok=True)
    results: list[MutationResult] = []

    for index, mutation in enumerate(mutations, start=1):
        mutant_dir = tmp_root / f"mutant_{index}_{mutation.id}"
        if mutant_dir.exists():
            shutil.rmtree(mutant_dir)
        shutil.copytree(source_parent, mutant_dir / "samples")
        write_suite(suite, mutant_dir)
        applied = _apply_mutation(mutant_dir / "samples" / package_name, mutation)
        if not applied:
            run = RunResult(
                ok=False,
                passed=0,
                failed=0,
                errors=1,
                coverage=None,
                stdout="",
                stderr=f"Mutation not applied: {mutation.label}",
                returncode=2,
            )
            results.append(MutationResult(mutation=mutation, killed=False, run=run))
            continue
        run = run_pytest(mutant_dir, package_parent=mutant_dir / "samples", package_name=package_name)
        results.append(MutationResult(mutation=mutation, killed=not run.ok, run=run))

    killed = sum(1 for result in results if result.killed)
    return MutationScore(killed=killed, total=len(results), results=tuple(results))


def apply_single_mutation(package_root: str | Path, mutation_id: str) -> bool:
    """Apply one catalog mutation in-place for the live Inject button."""
    mutation = next(item for item in MUTATIONS if item.id == mutation_id)
    return _apply_mutation(Path(package_root), mutation)


def _apply_mutation(package_root: Path, mutation: Mutation) -> bool:
    path = package_root / mutation.file
    text = path.read_text(encoding="utf-8")
    if mutation.find not in text:
        return False
    path.write_text(text.replace(mutation.find, mutation.replace, 1), encoding="utf-8")
    return True
