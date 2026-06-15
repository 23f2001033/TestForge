---
title: TestForge Characterization Lab
emoji: 🔨
colorFrom: teal
colorTo: amber
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
tags:
  - build-small-hackathon
  - sponsor:openai
  - openai-codex
  - testing
  - agent
---

# TestForge: Characterization Lab

Point TestForge at untested legacy Python code and it forges a green pytest suite that freezes the current behavior before you refactor.

The demo path is deterministic and needs no model or GPU:

1. Analyze public functions in `samples/legacy_repo`.
2. Pick compact input cases from signatures and type hints.
3. Execute the real function and capture the actual return value or exception.
4. Render pytest assertions from those captured facts.
5. Run the suite.
6. Mutate the source and report how many behavior changes the suite catches.
7. Export a PR-style patch that adds the generated tests.

## Trust Model

**Layer 1: capture then assert.** TestForge never asks a model what the output should be. It runs the real code first, then writes assertions against observed behavior. That makes the suite green by construction and prevents empty tests like `assert True`.

**Layer 2: mutation score.** A passing suite is not enough. TestForge applies a small deterministic mutation catalog and shows the headline metric: `Mutation score: X/Y behavior changes detected`.

**Layer 3: model enhancement.** Optional small-model input suggestions are left as an enhancement path. The shipped demo is intentionally model-free so judges can run it instantly.

## How Codex Built This

This repo was built end-to-end with OpenAI Codex in milestone commits:

- `Add legacy sample and AST analyzer`: created the untested legacy package and AST discovery for public functions.
- `Add deterministic capture runner`: added input inference, capture-then-assert rendering, subprocess pytest execution, and repo-local pytest temp handling.
- `Add deterministic mutation scoring`: added the hand-rolled mutation catalog and scoring loop.
- `Add forge app orchestration`: added agent orchestration, Gradio UI, live injected regression, and PR patch export.

The main engineering choice was to keep AI out of the source of truth. The current code is the authority; Codex built the agent that observes it, writes tests from observations, and then proves those tests can catch regressions.

## Run Locally

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python app.py
```

## Demo Arc

1. Click **Forge Tests**.
2. See the agent log, generated tests, green pytest result, coverage, and mutation score.
3. Click **Inject a regression**.
4. The same generated suite turns red on the controlled behavior change.
5. Download `testforge.patch` as a PR-ready artifact.

## Scope Notes

- Upload-your-own repo and model-assisted input search are intentionally cut for the deadline.
- The deterministic path is the qualifying demo: no GPU, no weights, no network.
- All generated tests call real public functions and assert captured returns or captured exceptions.
