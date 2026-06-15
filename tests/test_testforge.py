from pathlib import Path

from analyzer import analyze


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
