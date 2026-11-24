# CitrusScholar adapter guide

Baseline `d275430d3ef01bf9558ccd85204d1bdede631989`. The [capability migration chart](../CAPABILITY_MIGRATION.md) records the fixed release entry, deep host rules, API routes and open host acceptance items.

## Install

Install a read-only snapshot at `<native-skills-root>/nature-figure/SKILL.md` with `scripts/`, `references/`, `assets/` and `CAPABILITY_MIGRATION.md`. Carry `LICENSE`, `NOTICE` and the dependency locks with the release, and pin the package SHA. Mount that standard root under native `/skills/`. At baseline `01_src/src/agent/host.py` supplies the repository `skills/` to native discovery, and the legacy catalog separately pins version and digest. The host maintainer connects the new release root and preserves compatibility with the old snapshot. Keep `vendor/`, `tools/` and `tests/` outside runtime discovery. Provision the Python lock in the managed Worker and optional PDF QA separately.

## Bind and publish

1. Bind the authorized source attachment once. A version 1 input contract can bind a CSV file to the main script as a DataFrame using `tables: [{name: frame, input: source, format: csv}]`. In custom parsing, bind a raw Path and read that authorized snapshot once. Keep source hashes and read options. Embed the pure Python contents of `scripts/freeze_groups.py` in the preparation script. Call `tables = freeze_groups(frame)` and use `emit.table('observations', tables['observations'], parents=['source'])` and the corresponding `summary` call. `source` names the original authorized binding.
2. Call `run_research_figure_script` with `outputs_json` version `2` and declare `observations` and `summary` table outputs, both with parent `source`. Declare one figure with `formats: [svg]` and parents `observations` and `summary`. Use the literal contents of `scripts/render_grouped.py` followed by `fig = build_figure(data, view='observations')` as the `render_script`. The fresh renderer receives the declared frozen DataFrames as `data` and leaves one live Figure. No `emit`, raw path, analysis state, or `savefig` is needed in this renderer. The Worker handles export and manifests.
3. Verify and deliver the registered SVG before the next figure. For `means` and `counts`, bind the emitted typed `summary` dataset ref with the authorized typed table loader (`format: dataset`) or `load_dataset`. Forward that DataFrame as the new contract's frozen output parent. This forwarding needs no upload read or statistical calculation. Explicit composition uses one figure declaration and `view='combined'`, with both parent tables.

## Fresh renderer environment

The separated `render_script` does not run in the analysis process. At host commit `93b082f`, `packages/citrus_figures/core.py::capture_outputs` calls `capture_figure(source, namespace={"data": data}, check_layout=False)` inside `matplotlib.rcParamsDefault`. The renderer therefore receives these names:

| Name | Meaning |
| --- | --- |
| `__name__` | `"__citrusfig__"` |
| `data` | The declared frozen DataFrames, keyed by render alias or table parent |
| `plt` | `matplotlib.pyplot` (Agg) |
| `matplotlib` | The `matplotlib` package |
| `show` | A no-op |

Python's normal builtins are present. Nothing else is inherited from the analysis process. `np`, `pandas`, the analysis locals, the analysis input paths, the analysis rcParams and the analysis `emit` helper are absent. A renderer that needs NumPy must write `import numpy as np` itself; `import numpy` in the analysis script does not bind `np` here. A renderer that calls `emit.*` fails; the first return reports `render_script_emit_not_available` rather than a bare `NameError`.

Imports are allowed except the host's forbidden roots: `socket`, `http`, `urllib`, `requests`, `ftplib`, `smtplib`, `telnetlib`, `subprocess`, `multiprocessing`, `ctypes`, `pty`, `webbrowser`, `asyncio`. The Worker container, not this text check, is the security boundary.

When a required display calculation is small, prefer a pure-Python equivalent over importing a heavy module; do not change the sandbox to make an optional dependency appear. In the source repository, `tests/test_fresh_renderer.py` pins this scope and replays one missing-`np` renderer through a corrected renderer to a file-backed SVG receipt. `tests/fresh-renderer-standalone-missing-np.py.txt` is the failing shape; the two `fresh-renderer-standalone-fixed-*.py.txt` files show a self-import and a pure-Python revision.

## Two kinds of correction

1. **Source-only fix along the same run.** Send new `script` or `script_ref_json` together with `repair_from_run_id`, and nothing else. At `93b082f`, `01_src/src/research/script_runtime.py::execute_script_request` inherits the retained run's inputs, parameters, output contract and execution options. It requires the target run to be `failed` or `partial` with a complete `replay` of `input_snapshots` and `execution_options`; a `succeeded` run is rejected. Supplying any binding, parameter or other option alongside `repair_from_run_id` returns `script_execution_rejected` with status `not_run`. Use this when the data, contract, renderer identity and style stay fixed and only the code is wrong.
2. **Renderer or output-contract change.** Do not pass the old `repair_from_run_id`. Start a new run with explicit authorized bindings and the new contract. Reattach the same frozen tables through a typed `dataset_ref` binding (`format: dataset` or `load_dataset`) or through `analysis_result_ref_json`; this avoids a new upload read and avoids recomputing the statistics. A style-only change keeps the frozen tables and geometry; a changed scientific input or statistic requires a new freeze. If the host does not expose the exact handoff you need, report the missing capability to the host maintainer and say so; do not describe an unperformed reuse as completed.

A confirmed failure returns an observation with the failure stage, the innermost `<citrusfig>` line and an error code. Correct the cited portion, keep the unchanged inputs, and retry within the same run only through path 1. Syntax, shape and missing-name errors are correctable; an unknown external side effect is reconciled first.

## Host wiring (owned by the host)

- Record on the task: the method source (`explicit` selection, `auto` load, or inherited from the same goal), the package version and digest (release SHA and `SKILL.md` digest), and the figure specification. Inheritance is limited to the same goal; an unrelated new task does not inherit a prior method, and an explicit disable is not bypassed.
- `selected_skills=[]` is not evidence that no method was used; auto-load and same-goal inheritance are different facts from UI selection.
- Do not require every ordinary general figure request to read the full Skill before drawing. Apply the method when it is selected or inherited, and keep tool, network and execution permission a host decision.
- Delivery is a file card plus a short explanation after the SVG is registered. Do not paste the full SVG XML into the answer or the working context.
- This package has no terminal-state control. The host decides completion from the user's requested target and a registered, downloadable artifact. A plan, a probe, a statistics table or inline SVG text does not replace that artifact; an unrequested PDF or visual QA does not by itself make an otherwise delivered ordinary figure incomplete.

## Replay and export

The workbench owns replay and on-demand PDF/PNG creation from the selected revision. At `d275430`, the download route serves registered formats. The later host commit `36444ca` adds `POST /api/v2/figures/projects/{figure_id}/export/{fmt}` with `expected_revision` to generate a missing format. Validate the returned figure, format and revision and compare the downloaded bytes with the registered SHA-256 during acceptance. Style-only replay uses the existing statistics. Preserve renderer and frozen data identities, stable object locators and any mapping to managed Artists. Confirm the Worker uses licensed managed fonts and keeps explicit font filenames when applying styles.

Acceptance F01–F05 belongs to the integrated host. Exercise real model invocation, publication order, retained output after later failure, supported style changes and workbench export from an SVG-only project. The standalone smoke establishes the portable contract. Service state, browser behavior, account-scoped authorization, strict Worker startup and actual workbench exports require their own installed-host evidence.
