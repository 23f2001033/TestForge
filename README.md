---
title: TestForge
emoji: "🔨"
colorFrom: teal
colorTo: amber
sdk: gradio
sdk_version: 4.44.0
python_version: "3.12"
app_file: app.py
pinned: false
license: mit
tags:
  - build-small-hackathon
  - sponsor:openai
  - openai-codex
  - testing
  - agent
  - python
  - pytest
  - developer-tools
short_description: Freeze legacy Python behavior before refactoring
---

# 🔨 TestForge — Characterization tests for legacy Python code

**Track:** OpenAI Codex · **Prize target:** Best Use of Codex

Untested legacy Python code is scary to change because you do not know what
behavior you are about to break. **TestForge** points at a small Python repo,
discovers its public functions, executes the real code on representative inputs,
and generates a green pytest suite that locks in current behavior. Then it
proves the suite is not fake confidence by mutating the code and showing a
headline **mutation score**.

> Built as **a coding agent built by a coding agent**. The goal is not "AI
> writes tests." The goal is "AI creates a runnable, inspectable, regression-
> catching safety net before you refactor."

---

## Why this is trustworthy: the code verifies itself

The core design choice is **capture-then-assert**.

For every discovered function, TestForge chooses a few inputs, **runs the real
function**, records the actual return value or exception, and only then emits
pytest assertions.

```python
def test_apply_discount_case_1():
    assert apply_discount(100.0, 10.0) == 90.0

def test_with_tax_case_4():
    with pytest.raises(ValueError):
        with_tax(100.0, -1.0)
```

This means:

- every generated test is green on the current code by construction
- every test calls a real public function, so it cannot collapse into `assert True`
- the expected value comes from execution, not model guesswork

Then TestForge applies a fixed catalog of source mutations and reruns the same
generated suite. The result is a visible quality metric like:

```text
Mutation score: 7/9 behavior changes detected
```

That turns "the AI made tests" into "the AI made tests that demonstrably catch
regressions."

---

## Models

This shipped version is intentionally **deterministic and model-free** so the
demo works with **no model and no GPU**.

| Job | Current implementation | Fallback |
|---|---|---|
| Input generation | Type-hint-driven deterministic cases | Fixed mixed literals |
| Test expectation generation | Real code execution | None needed |
| Quality proof | Hand-rolled mutation scoring | None needed |

This keeps the demo fast, inspectable, and stable under hackathon time
pressure. A future enhancement path is to let a small coder model propose extra
edge-case inputs, but only accept those cases if they improve coverage or the
mutation score.

---

## How it works

```text
Pick bundled legacy repo
  -> Analyze        : AST discovery of public functions and signatures
  -> Generate       : choose deterministic inputs and capture real outputs
  -> Render         : write pytest characterization tests
  -> Run            : execute pytest in a subprocess
  -> Score          : apply deterministic mutations and count killed mutants
  -> Export         : produce a PR-style patch adding tests/
```

## Run locally

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python app.py
```

Then click **Forge Tests** to generate a full suite for the bundled sample repo,
inspect the generated tests, and see the mutation score. Click **Inject a
regression** to watch the same suite turn red on a controlled behavior change.

## Tests

```bash
python -m pytest -q
```

The project's own test suite currently covers:

- analyzer discovery and arity checks
- capture of returned values and raised exceptions
- deterministic suite generation staying green
- runner parsing for passing and failing suites
- deterministic mutation scoring
- PR patch export
- forge pipeline smoke path
- injected regression causing exactly one failure

## Project layout

```text
app.py                 Gradio UI + orchestration
agent.py               forge pipeline for the bundled sample repo
analyzer.py            AST discovery of public functions and methods
generator.py           deterministic inputs, capture, and pytest rendering
runner.py              subprocess pytest execution and parsing
mutator.py             hand-rolled mutation catalog and mutation score
patch.py               PR-style unified diff export
inject.py              controlled one-click demo regression
samples/legacy_repo/   bundled untested Python target repo
tests/test_testforge.py
```

## Demo arc

1. Click **Forge Tests**
2. Watch TestForge analyze the sample repo and generate tests from real execution
3. See a green pytest result and the mutation score
4. Click **Inject a regression**
5. Watch the same suite fail on exactly one controlled change
6. Download `testforge.patch` as a PR-style artifact

## Codex build log

This repo was built in milestone commits through OpenAI Codex:

- `Add legacy sample and AST analyzer`
- `Add deterministic capture runner`
- `Add deterministic mutation scoring`
- `Add forge app orchestration`
- `Document hackathon submission`

The most important product decision was keeping the **source of truth in the
code itself**, not in the model. Codex built the tooling and loop around that
principle.

## Privacy

The bundled target repo is synthetic and local. The deterministic demo path
uses no external model, no database, and no persistent user storage.

---

## Submission links

- 🤗 **Live Space:** add your Hugging Face Space URL here
- 🎥 **Demo video:** add your demo video link here
- 📣 **Social post:** add your social post link here
