"""Agent orchestration for TestForge."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from analyzer import Analysis, analyze
from generator import GeneratedSuite, generate_suite, write_suite
from inject import reset_sample
from mutator import MUTATIONS, Mutation, MutationScore, mutation_score
from patch import write_patch
from runner import RunResult, run_pytest


ROOT = Path(__file__).resolve().parent
SAMPLES_ROOT = ROOT / "samples"
LEGACY_ROOT = SAMPLES_ROOT / "legacy_repo"
RUNS_ROOT = ROOT / "generated" / "runs"


@dataclass(frozen=True)
class ForgeArtifacts:
    run_dir: Path
    analysis: Analysis
    suite: GeneratedSuite
    green: RunResult
    mutation: MutationScore
    patch_path: Path
    logs: tuple[str, ...]


def forge_legacy_repo(
    max_cases_per_function: int = 4,
    mutations: tuple[Mutation, ...] = MUTATIONS,
) -> ForgeArtifacts:
    """Run the deterministic TestForge pipeline for the bundled sample."""
    run_dir = _fresh_run_dir()
    logs: list[str] = []

    logs.append("Target: bundled legacy_repo with zero tests")
    reset_sample(SAMPLES_ROOT, run_dir)

    analysis = analyze(run_dir / "samples" / "legacy_repo", package="legacy_repo")
    logs.append(f"Analyzed {len(analysis.functions)} public functions")
    for fn in analysis.functions:
        logs.append(f"  - {fn.module}.{fn.qualname}({', '.join(fn.parameters)})")

    suite = generate_suite(analysis, max_cases_per_function=max_cases_per_function)
    write_suite(suite, run_dir)
    logs.append(f"Captured {suite.assertion_count} behaviors into {len(suite.files)} test files")

    green = run_pytest(run_dir, package_parent=run_dir / "samples")
    logs.append(f"Suite run: {green.summary}")
    if green.coverage is not None:
        logs.append(f"Coverage: 0% -> {green.coverage:.0f}%")
    else:
        logs.append("Coverage: pytest-cov unavailable locally; suite still ran green")

    mutation = mutation_score(run_dir / "samples", suite, run_dir / "mutants", mutations=mutations)
    logs.append(f"Mutation score: {mutation.headline()} ({mutation.percent:.1f}%)")
    for survived in mutation.survived:
        logs.append(f"  survived: {survived.label}")

    patch_path = write_patch(suite, run_dir / "testforge.patch")
    logs.append(f"Patch ready: {patch_path.name}")

    return ForgeArtifacts(
        run_dir=run_dir,
        analysis=analysis,
        suite=suite,
        green=green,
        mutation=mutation,
        patch_path=patch_path,
        logs=tuple(logs),
    )


def _fresh_run_dir() -> Path:
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="testforge_", dir=RUNS_ROOT))
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path
