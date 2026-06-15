from pathlib import Path
import shutil
import sys

from analyzer import analyze
from generator import capture, generate_suite, write_suite
from mutator import MUTATIONS, mutation_score
from runner import run_pytest
from samples.legacy_repo.pricing import apply_discount, with_tax


ROOT = Path(__file__).resolve().parents[1]
LEGACY_ROOT = ROOT / "samples" / "legacy_repo"


def test_analyzer_discovers_expected_public_functions():
    analysis = analyze(LEGACY_ROOT, package="legacy_repo")
    discovered = {(fn.module, fn.qualname, fn.arity) for fn in analysis.functions}

    assert discovered == {
        ("legacy_repo.dates", "days_between", 2),
        ("legacy_repo.dates", "is_weekend", 1),
        ("legacy_repo.invoice", "invoice_total", 1),
        ("legacy_repo.invoice", "line_total", 2),
        ("legacy_repo.pricing", "apply_discount", 2),
        ("legacy_repo.pricing", "bulk_price", 2),
        ("legacy_repo.pricing", "with_tax", 2),
        ("legacy_repo.slugify", "slugify", 1),
        ("legacy_repo.slugify", "truncate", 2),
    }


def test_analyzer_keeps_hints_docstrings_and_source():
    analysis = analyze(LEGACY_ROOT, package="legacy_repo")
    fn = next(item for item in analysis.functions if item.qualname == "apply_discount")

    assert fn.type_hints == {"price": "float", "pct": "float"}
    assert fn.return_hint == "float"
    assert "percentage discount" in fn.docstring
    assert "def apply_discount" in fn.source


def test_capture_records_return_and_exception():
    sys.path.insert(0, str((ROOT / "samples").resolve()))
    analysis = analyze(LEGACY_ROOT, package="legacy_repo")
    discount = next(item for item in analysis.functions if item.qualname == "apply_discount")
    tax = next(item for item in analysis.functions if item.qualname == "with_tax")

    assert apply_discount(100, 10) == 90.0
    returned = capture(discount, [(100.0, 10.0)])
    raised = capture(tax, [(100.0, -1.0)])

    assert returned[0].value_repr == "90.0"
    assert raised[0].exception_type == "ValueError"


def test_deterministic_generated_suite_is_green(tmp_path):
    analysis = analyze(LEGACY_ROOT, package="legacy_repo")
    suite = generate_suite(analysis)
    workdir = tmp_path / "work"
    shutil.copytree(ROOT / "samples", workdir / "samples")
    write_suite(suite, workdir)

    result = run_pytest(workdir, package_parent=workdir / "samples")

    assert result.ok, result.stdout + result.stderr
    assert result.passed == suite.assertion_count
    assert result.coverage is None or result.coverage >= 0


def test_runner_parses_known_good_and_bad(tmp_path):
    good = tmp_path / "good"
    good.mkdir()
    (good / "tests").mkdir()
    (good / "tests" / "test_ok.py").write_text("def test_ok():\n    assert 1 == 1\n", encoding="utf-8")
    good_result = run_pytest(good, with_coverage=False)

    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "tests").mkdir()
    (bad / "tests" / "test_bad.py").write_text("def test_bad():\n    assert 1 == 2\n", encoding="utf-8")
    bad_result = run_pytest(bad, with_coverage=False)

    assert good_result.ok
    assert good_result.passed == 1
    assert not bad_result.ok
    assert bad_result.failed == 1


def test_mutation_score_is_deterministic_and_kills_known_mutant(tmp_path):
    analysis = analyze(LEGACY_ROOT, package="legacy_repo")
    suite = generate_suite(analysis)
    score = mutation_score(ROOT / "samples", suite, tmp_path / "mutants")

    assert score.total == len(MUTATIONS)
    assert score.killed > 0
    known = next(
        result for result in score.results if result.mutation.id == "bulk_multiply_to_divide"
    )
    assert known.killed
