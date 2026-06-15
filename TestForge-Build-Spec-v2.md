# BUILD SPEC v2 — "TestForge: Characterization Lab"
## Autonomous agent that freezes legacy Python behavior before you refactor — and *proves* its tests catch bugs
## Build Small Hackathon · Primary prize: OpenAI "Best Use of Codex" ($10k) · Free stacks: MiniCPM, Best Demo
## THIS DOCUMENT IS THE SINGLE SOURCE OF TRUTH. Feed it to OpenAI Codex as-is. (Supersedes v1.)

---

## 0. CONTEXT FOR CODEX (read first)

You are building a **Gradio app** deployed as a **Hugging Face Space** with a **connected GitHub repo**. It is an **agent that writes a passing pytest suite for any small Python codebase, runs it, repairs it until green, then proves the suite's *quality* with a mutation score** — and exports the result as a PR-style patch.

The pitch in one line: **"Point it at untested legacy code → get a green characterization-test suite that provably catches regressions, in under a minute, with zero GPU required."**

Hard constraints (non-negotiable):
1. **Build this entirely with OpenAI Codex** in a **fresh GitHub repo** connected to the Space. The $10k prize requires **Codex-attributed commits** and rewards *complex, holistic* usage. Commit in meaningful increments; keep a "How Codex built this" log.
2. Any ML model must be **< 32B params** and **optional**: the app must run and fully demo **with no model and no GPU** via the deterministic backbone (§3). Bias toward **WORKING DEMO > feature count.**
3. **Deadline: June 15, 23:59 UTC — hours away.** Build in the priority order of §9. Ship the deterministic core first; everything else is enhancement.

Why this wins: it is **a coding agent built by a coding agent**, its output is **objectively verifiable** (tests run; mutation score is a number, not a vibe), and the demo is a 30-second **0%→green→mutation-proof** arc.

---

## 1. THE TRUST MODEL (this is the whole project — get it exactly right)

Three layers, in order of importance:

### Layer 1 — Capture-then-assert backbone (deterministic, MANDATORY, no model/GPU)
Do **not** ask a model "what should this return?" — unverifiable. Instead **execute the real function** on chosen inputs, record the actual output (or the exception raised), then emit:
```python
def test_add_two_positives():
    assert calculator.add(2, 3) == 5          # 5 captured by executing add(2,3)

def test_divide_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        calculator.divide(1, 0)               # exception captured by execution
```
Consequences: every generated test is **green on the current code by construction**, contains a **real assertion on a real public call** (so it physically *cannot* be `assert True`), and goes **red if behavior changes**. Correctness never depends on the model.

### Layer 2 — Mutation score (the HEADLINE quality metric — judges' "oh, this is real" moment)
A green suite is worthless if it catches nothing. So measure whether the suite actually detects behavior changes: apply a fixed catalog of small source mutations to the target, run the generated suite against each mutant, and count how many mutants are **killed** (≥1 test fails). Display prominently: **`Mutation score: 7/9 behavior changes detected`**.
- **Hand-roll the mutants — do NOT pull in mutmut/cosmic-ray** (too slow/heavy for a live demo). Keep the set small, deterministic, and fast (≤ a few seconds). See §4.

### Layer 3 — Model enhancement (OPTIONAL, gated by Layer 2)
A small coder model proposes *additional* input cases / edge cases per function. A model-suggested case is **accepted only if adding its captured assertion raises the mutation score or coverage** — otherwise it's discarded. This makes the model **provably earn its place** and keeps the agent loop honest. The demo must still hit full marks with the model OFF.

---

## 2. THE AGENT LOOP (the "complex agent" — narrate it in UI + README)

`agent.py` runs an explicit, streamed loop:
```
analysis = analyze(target)                      # public functions/classes (§5)
suite = []
for fn in analysis.functions:
    cases = deterministic_inputs(fn)            # Layer 1
    if model_on: cases += model_inputs(fn)      # Layer 3 candidates
    for attempt in range(MAX_REPAIR):           # e.g. 3
        captured = capture(fn, cases)           # EXECUTE to record outputs/exceptions
        test = render_test(fn, captured)
        res  = run_pytest(test)                 # subprocess
        if res.ok: break
        cases = repair(fn, cases, res.error)    # drop bad-arity/erroring candidates
    suite.append(test); log(fn.name, res)
write_suite(suite)
green   = run_pytest(suite)                      # whole-suite green check
cov     = coverage(target, suite)               # Layer-2 support
mutscore= mutation_score(target, suite)         # Layer 2 (§4)
if model_on: suite = keep_only_value_adding(suite, mutscore, cov)  # Layer 3 gate
patch   = make_pr_patch(suite)                   # §6
```
Expose `MAX_REPAIR`, the model toggle, and target selection in the UI. Stream every step.

---

## 3. MODELS (optional, small, prize-stacking — never load-bearing)

| Job | Primary | Params | Fallback |
|---|---|---|---|
| Propose extra/edge input cases + readable test names | a small **coder** model: `Qwen/Qwen2.5-Coder-7B-Instruct` (or a MiniCPM code/instruct ≤8B if it loads cleanly) | ≤8B | **deterministic input strategy** (no model) |

- Model returns JSON: per function, candidate input tuples + a name slug. **Validate everything** (arity, JSON-parse); expected values always come from real execution.
- ZeroGPU: apply `@spaces.GPU` only when `import spaces` succeeds (no-op locally). ONE GPU acquisition per "Forge" click; loop inside. Check availability with `transformers.utils.is_torch_available()`, not bare `import torch`. Cache the load; never hold a CUDA context across calls.
- Use a **MiniCPM** model where it works to also qualify for the OpenBMB prize, and state the param math in the README. Optionally run inference on **Modal** and note it in the README for the Modal prize — but only if it costs no time.

---

## 4. MUTATION ENGINE (`mutator.py`) — hand-rolled, fast, deterministic

Apply each mutation to a **copy** of the target in a temp dir, run the suite, restore. Catalog (~9 operators; AST or careful regex):
- Arithmetic: `+`↔`-`, `*`↔`/`
- Comparison: `==`→`!=`, `<`→`>=`, `>`→`<=`
- Boolean/constant: `and`→`or`, `True`→`False`, numeric literal `n`→`n+1`
- Control: one function's `return X` → `return None`

For each applied mutant: `killed = (run_pytest(suite) has ≥1 failure)`. **Mutation score = killed / total_mutants.** Keep total small and stable so the demo number is reproducible. A surviving mutant (not killed) is a real gap — list it in the UI ("survived: `pricing.py` `*`→`/`") to show honesty.

---

## 5. ANALYZER (`analyzer.py`)
Use `ast` to discover **public** top-level functions and class methods (skip names starting with `_`). For each: module path, qualified name, parameter names, type hints (if any), docstring, source snippet. Build a simple import map so generated tests import correctly. Skip functions with side effects you can't safely call (I/O, network) — restrict the bundled sample to **pure** functions so this is a non-issue for the demo; for uploads, wrap capture in try/except and skip on error.

---

## 6. RUNNER & PATCH
- `runner.py`: run `pytest` (+ `coverage`/`pytest-cov`) in a **subprocess** with a timeout, parse passed/failed/errors and coverage %. Never `exec` untrusted code in-process; sandbox uploaded targets to a temp dir and run capture inside the subprocess too.
- `patch.py`: emit a **PR-style unified diff / git patch** that adds the `tests/` directory (and a one-line CI hint). This is the downloadable artifact — feels like real agent work, better than a zip.

---

## 7. GRADIO APP SPEC

### 7.1 Layout (single page; lab/forge aesthetic, not a boring dashboard)
```
TestForge — Characterization Lab
Freeze what your code does today. Refactor without fear.
[Target ▾  (bundled "legacy_repo" | upload .zip)]   [☑ Use small coder model]   [🔨 Forge Tests]
─ Agent log (streaming): "analyzed 9 functions… add(): 3 cases captured… repairing slugify… suite green ✅"
─ Generated tests (file tabs, syntax-highlighted)        │   ✅ 27 passed / 0 failed
─ Coverage:  0%  →  81%        Mutation score:  7/9 behavior changes detected   (survived: 2 — listed)
─ [💣 Inject a regression] → same suite → "❌ 1 failed: expected 5, got 6 (caught!)"
─ [⬇ Download PR patch]
```

### 7.2 Notes
- **Bundle a messy demo target** `samples/legacy_repo/` with **no tests** (see §8). The two-click arc — **Forge Tests** then **Inject a regression** — IS the demo; both buttons are mandatory. (Mutation score is the static proof; Inject is the live theatrical proof. Keep both.)
- Stream the agent log via generators so the loop is visible.

### 7.3 File structure
```
app.py            # Gradio UI + orchestration
agent.py          # generate→run→repair→mutation-gate→stop loop (§2)
analyzer.py       # ast discovery (§5)
generator.py      # deterministic + model inputs; capture(); render_test()
runner.py         # pytest+coverage subprocess + parsing (§6)
mutator.py        # hand-rolled mutation catalog + score (§4)
patch.py          # PR-style unified diff export (§6)
inject.py         # one-click demo regression (apply/undo)
samples/legacy_repo/   # invoice.py, dates.py, slugify.py, pricing.py (+__init__), NO tests
tests/test_testforge.py   # the project's OWN deterministic tests (§10)
requirements.txt
README.md         # frontmatter submission tags + "How Codex built this" (§11)
```

---

## 8. SAMPLE / DEMO TARGET (build this FIRST — everything depends on it)
`samples/legacy_repo/` — small, pure, deterministic, type-hinted, **untested**:
- `pricing.py`: `apply_discount(price, pct)`, `with_tax(amount, rate)`, `bulk_price(unit, qty)`
- `invoice.py`: `line_total(qty, unit)`, `invoice_total(lines)`
- `dates.py`: `days_between(a, b)`, `is_weekend(d)`
- `slugify.py`: `slugify(s)`, `truncate(s, n)`
These are also fixtures for the project's own tests (§10). Pick functions where the mutation catalog clearly bites (arithmetic in pricing/invoice, comparisons in dates) so the mutation score is impressive.

---

## 9. PRIORITY ORDER / CUT LIST (build top-down; cut from the bottom)
**MUST (the demo):**
1. `samples/legacy_repo/` + `analyzer.py`
2. Capture-then-assert generation + `runner.py` → green suite + coverage
3. `mutator.py` → mutation score in the UI
4. Gradio UI with streaming log + **Forge** + **Inject** + **Download patch**
5. Project's own tests (§10) + README with Codex write-up + submission tags

**NICE (add only if time remains):** model enhancement layer (§ Layer 3) · upload-your-own-zip · run-existing-tests-first · import-map polish · Modal inference.

**NEVER cut:** bundled sample, capture-then-assert backbone, mutation score, the Forge→Inject demo arc, README + Codex attribution.

---

## 10. THE PROJECT'S OWN TESTS (`tests/test_testforge.py` — deterministic, model-free)
1. **Analyzer** discovers the exact expected public-function set with correct arities.
2. **Capture:** `capture(apply_discount,[(100,10)])` records `90.0`; a divide-by-zero case records a `ZeroDivisionError`.
3. **Backbone green:** with model OFF, the generated suite for `legacy_repo` is **100% green**.
4. **Mutation works:** mutation score on the generated suite is **> 0** and deterministic; a known mutant (e.g. `*`→`/` in `bulk_price`) is **killed**.
5. **Inject:** `inject.apply()` causes **exactly one** generated test to fail; `inject.undo()` restores green.
6. **Runner parsing** reports correct counts for a known-good and known-bad file.
7. **Model gate (if built):** a no-value model case is **rejected** (mutation score unchanged).
Use a local pytest basetemp on Windows if needed.

---

## 11. CODEX ATTRIBUTION + SUBMISSION (or the $10k won't count)
1. **Fresh GitHub repo, built end-to-end via OpenAI Codex.** Connect it to the Space. Commit per milestone (analyzer → generation → runner → mutator → UI → demo) with clear messages.
2. README **"How Codex built this"** section: the analyze→capture→run→repair→mutation-gate loop you had Codex implement, repair iterations, design choices. Depth scores; light usage doesn't.
3. HF Space `README.md` frontmatter carries submission tags (the field-guide reads them). **Verify the exact Codex/OpenAI tag** in the field guide (https://build-small-hackathon-field-guide.hf.space/):
   ```yaml
   sdk: gradio
   app_file: app.py
   tags:
     - build-small-hackathon
     - sponsor:openai        # confirm exact tag for the Codex prize
     - openai-codex
     - testing
     - agent
     - minicpm               # only if a MiniCPM model is actually used
   ```
   **Never strip these tags** — re-uploading a README without them un-submits the project.
4. **Focus discipline:** Codex is the $10k target. Best Demo / MiniCPM / Tiny Titan should come *for free* if you qualify — do **not** add scope to chase them. Unlimited submissions are allowed; submit early, keep improving.

---

## 12. DEFINITION OF DONE
- [ ] Judge clicks **Forge Tests** on the bundled `legacy_repo` → streaming agent log → **100% green** suite + **coverage 0%→X** in <30s, **no GPU/model needed**.
- [ ] **Mutation score** is shown (e.g. 7/9), with surviving mutants listed honestly.
- [ ] **Inject a regression** turns the same suite **red** on exactly the mutated function, with a readable diff.
- [ ] **Download PR patch** yields a real, applyable diff that adds a runnable `tests/`.
- [ ] The project's own `pytest` suite (§10) is green.
- [ ] Repo built via **Codex-attributed commits**; README has the Codex write-up + submission tags.
- [ ] Space public + runs; demo video + social post linked.
- [ ] All models (if any) ≤32B; param math in README.

---

## 13. TIME-BOXED PLAN (for the hours left — adjust to taste)
1. **0:00–0:30** — `legacy_repo` sample + `analyzer.py` + project skeleton; first Codex commits.
2. **0:30–1:30** — capture-then-assert `generator.py` + `runner.py`; green suite on the sample.
3. **1:30–2:15** — `mutator.py` + mutation score; wire coverage.
4. **2:15–3:15** — Gradio UI: streaming log, Forge/Inject/Download patch.
5. **3:15–3:45** — project's own tests (§10); fix what they catch.
6. **3:45–4:30** — README (Codex write-up + tags), deploy to Space, record 90s demo, post.
7. **Remaining** — optional model-enhancement layer; otherwise stop and submit.

---

## 14. DEMO VIDEO SCRIPT (~90s — OBS/Loom, 1080p, captions)
| Time | On screen | Narration |
|---|---|---|
| 0:00–0:10 | Title | "Refactoring untested legacy code is terrifying — you can't tell what you broke. TestForge freezes the current behavior first." |
| 0:10–0:28 | Pick `legacy_repo` → **Forge Tests** → streaming log | "It's an agent: it analyzes every function, picks inputs, and **runs the real code to capture the true output**, then writes a test asserting exactly that — green by construction." |
| 0:28–0:45 | Green suite + coverage 0%→81% | "Seconds later: a full passing suite, **no GPU**, coverage from zero to eighty-one percent." |
| 0:45–1:05 | Mutation score 7/9 (+ survived list) | "But passing tests can be worthless. So it **mutates the source and proves the tests catch the changes** — seven of nine behavior changes detected, and it's honest about the two it missed." |
| 1:05–1:18 | **Inject a regression** → red diff | "Live: I break a function… the same suite goes **red**, exact assertion, expected 5 got 6. Caught." |
| 1:18–1:30 | Download patch + README "How Codex built this" | "Export a PR-ready patch. And the whole agent was built end-to-end with **OpenAI Codex**. A coding agent, built by a coding agent, that proves its own work." |

**Tip:** demo the deterministic path on camera (instant, never fails); lead the social post with the green→mutation→red GIF.
