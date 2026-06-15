from __future__ import annotations

from pathlib import Path

import gradio as gr

from agent import forge_legacy_repo
from inject import reset_sample, run_injected_suite


LAST_RUN: dict[str, Path] = {}


CSS = """
:root {
  --tf-ink: #171717;
  --tf-muted: #595959;
  --tf-line: #d6d3d1;
  --tf-panel: #fafaf9;
  --tf-accent: #0f766e;
  --tf-warn: #b45309;
}
.gradio-container {
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--tf-ink);
}
.tf-title h1 {
  font-size: 34px;
  line-height: 1.1;
  letter-spacing: 0;
  margin-bottom: 4px;
}
.tf-title p {
  color: var(--tf-muted);
  margin-top: 0;
}
.tf-metric {
  border: 1px solid var(--tf-line);
  background: var(--tf-panel);
  border-radius: 8px;
  padding: 14px;
}
"""


def forge(use_model: bool, max_cases: int):
    del use_model  # deterministic backbone is the demo path.
    artifacts = forge_legacy_repo(max_cases_per_function=max_cases)
    LAST_RUN["run_dir"] = artifacts.run_dir
    log = "\n".join(artifacts.logs)
    preview = _suite_preview(artifacts.suite.files)
    result_md = _result_markdown(artifacts)
    return log, preview, result_md, str(artifacts.patch_path), gr.update(interactive=True)


def inject_regression():
    run_dir = LAST_RUN.get("run_dir")
    if run_dir is None:
        return "Forge tests first.", "No run yet."

    reset_sample(Path(__file__).resolve().parent / "samples", run_dir)
    result = run_injected_suite(run_dir)
    status = "caught" if not result.run.ok else "survived"
    summary = (
        f"Injected: {result.mutation_label}\n"
        f"Result: {result.run.summary} ({status})\n\n"
        f"{_first_failure(result.run.stdout)}"
    )
    return summary, result.run.stdout[-4000:]


def _suite_preview(files: dict[str, str]) -> str:
    parts: list[str] = []
    for name, content in sorted(files.items()):
        parts.append(f"# {name}\n{content}")
    return "\n\n".join(parts)


def _result_markdown(artifacts) -> str:
    survived = artifacts.mutation.survived
    survived_text = "\n".join(f"- {item.label}" for item in survived) or "- None"
    coverage = "not installed locally" if artifacts.green.coverage is None else f"{artifacts.green.coverage:.0f}%"
    return f"""
### Forge Result

**Suite:** {artifacts.green.summary}  
**Coverage:** 0% -> {coverage}  
**Mutation score:** {artifacts.mutation.headline()} ({artifacts.mutation.percent:.1f}%)

**Surviving mutants**
{survived_text}
"""


def _first_failure(output: str) -> str:
    lines = output.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("FAILED ") or "E       AssertionError" in line:
            return "\n".join(lines[max(0, index - 4) : index + 10])
    return "\n".join(lines[-20:])


with gr.Blocks(css=CSS, title="TestForge Characterization Lab") as demo:
    gr.HTML(
        """
        <div class="tf-title">
          <h1>TestForge -- Characterization Lab</h1>
          <p>Freeze what legacy Python code does today. Refactor without fear.</p>
        </div>
        """
    )
    with gr.Row():
        target = gr.Dropdown(
            ["bundled legacy_repo"],
            value="bundled legacy_repo",
            label="Target",
            interactive=False,
        )
        use_model = gr.Checkbox(False, label="Use small coder model")
        max_cases = gr.Slider(2, 4, value=4, step=1, label="Cases per function")
        forge_btn = gr.Button("Forge Tests", variant="primary")

    with gr.Row():
        log = gr.Textbox(label="Agent log", lines=14)
        results = gr.Markdown(label="Results")

    tests_preview = gr.Code(label="Generated tests", language="python", lines=18)

    with gr.Row():
        inject_btn = gr.Button("Inject a regression", interactive=False)
        patch_file = gr.File(label="Download PR patch")

    with gr.Row():
        inject_summary = gr.Textbox(label="Inject result", lines=8)
        inject_output = gr.Textbox(label="Pytest output", lines=8)

    forge_btn.click(
        forge,
        inputs=[use_model, max_cases],
        outputs=[log, tests_preview, results, patch_file, inject_btn],
    )
    inject_btn.click(inject_regression, outputs=[inject_summary, inject_output])


if __name__ == "__main__":
    demo.launch()

