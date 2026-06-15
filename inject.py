"""One-click live regression demo."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from mutator import MUTATIONS, apply_single_mutation
from runner import RunResult, run_pytest


INJECT_MUTATION_ID = "bulk_threshold_ge_to_gt"


@dataclass(frozen=True)
class InjectResult:
    mutation_label: str
    run: RunResult


def reset_sample(source_parent: str | Path, run_dir: str | Path) -> Path:
    """Copy samples into a runnable demo directory."""
    source_parent = Path(source_parent).resolve()
    run_dir = Path(run_dir).resolve()
    sample_target = run_dir / "samples"
    if sample_target.exists():
        shutil.rmtree(sample_target)
    shutil.copytree(source_parent, sample_target)
    return sample_target / "legacy_repo"


def apply(run_dir: str | Path, package_name: str = "legacy_repo") -> bool:
    package_root = Path(run_dir).resolve() / "samples" / package_name
    return apply_single_mutation(package_root, INJECT_MUTATION_ID)


def run_injected_suite(run_dir: str | Path, package_name: str = "legacy_repo") -> InjectResult:
    mutation = next(item for item in MUTATIONS if item.id == INJECT_MUTATION_ID)
    applied = apply(run_dir, package_name=package_name)
    if not applied:
        raise RuntimeError(f"Could not apply inject mutation: {mutation.label}")
    run_dir = Path(run_dir).resolve()
    result = run_pytest(run_dir, package_parent=run_dir / "samples", package_name=package_name)
    return InjectResult(mutation_label=mutation.label, run=result)
