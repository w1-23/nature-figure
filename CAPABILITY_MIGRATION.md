# CitrusScholar capability migration

The fixed host baseline is `d275430d3ef01bf9558ccd85204d1bdede631989`. The host checkout advanced during review to `36444cac80fdd1105a72f1a957d32cac4bbbf5d3`. The newer commit retains the hosted `SKILL.md`, `ADAPTER.md`, catalog and deep host policy from the baseline and adds missing-format export. This chart describes committed source. The independent upstream pin is `Yuan1z0825/nature-skills` at `c6701dbea29afa7c596d029b957b7edc92130ea5`, manifest `2.8.0`. See [upstream migration](MIGRATION.md) and [attribution](NOTICE).

## Entry and deep rules

`01_src/src/agent/host.py` points native discovery at the release's `skills/` directory, mounted at `/skills/` by `01_src/src/agent/deep_agent_runtime.py`. The fixed release supplies its own `skills/nature-figure/SKILL.md` v`3.0.0`. `01_src/src/agent/research_skill_catalog.py` pins the curated snapshot at digest `2660ac78e3602c2e9fa3e6cd0e88d6997f1335d408c0de66d142041cb03f41b9`. Its separate CLI adapter refers to `citrusscholar-support` 2.0.0 and upstream `7bff1d0539c0dfad6c30178bb93ce6dd8a5cebf8`. These identities belong to the existing release. Installation of this independent package is pending host integration.

`01_src/src/agent/host_policy.py` applies figure guidance when the corresponding tools are exposed. It calls for scientific purpose, data and units, experimental unit and sample size, evidence roles for panels, justified uncertainty, SVG by default, explicit composition, and style edits on saved scientific content. It points to `nature-figure/references/figure-methods.md`, which this package supplies at the same relative path. Tool, network and execution permissions remain host decisions.

| Capability | Fixed host boundary | Independent adaptation |
| --- | --- | --- |
| Entry and selection | Native discovery uses the standard directory. Legacy sessions resolve catalog snapshots by their registered identity. | Install [SKILL.md](SKILL.md) with the [adapter](references/citrus-host-adapter.md), lock and provenance. Keep the prior digest available. Use configured managed Python directly. Keep raw upstream routing and assets outside runtime discovery. |
| Data preparation | `inputs_json` binds authorized files or `dataset_ref` values to names. `outputs_json.input_contract` v1 distinguishes raw `Path` bindings from typed CSV, TSV, Excel and `dataset` DataFrames. | Read the authorized source once. Use original binding names for table lineage. Retain exact raw observations and group-keyed statistics. Reuse a typed dataset via `format: dataset` or `load_dataset` for subsequent figures. Ordinary attachment plotting uses local compute. |
| Worker | `run_research_figure_script` uses `outputs_json` v2 with at most eight tables and eight figures in one contract. | Use `emit.table(name, frame, parents=[original_binding])` in preparation. A fresh `render_script` receives frozen DataFrames in `data` keyed by declared parents or `input_contract.render` aliases. It leaves exactly one Matplotlib `Figure`. Keep input reads, aggregation, `emit` and `savefig` out of the renderer. Only `data`, `__name__`, `plt`, `matplotlib` and `show` are supplied; the renderer imports any other module itself. The Worker owns export. |
| Delivery and repair | The Worker supports multiple named outputs. The deep policy defaults to SVG and preserves explicitly requested compositions and formats. | Declare and publish one verified SVG per independent logical figure before proceeding to the next. An explicit composition stays one multi-panel Figure. Retain earlier deliverables after a later failure. A source-only fix reuses the retained failed or partial run via `repair_from_run_id`; a changed renderer or output contract starts a new run that reattaches the frozen tables by `dataset_ref`. |
| Replay and editing | The workbench binds supported object/property locators to the current revision. Frozen replay checks the saved evidence and scientific geometry. | Preserve frozen input and renderer identities, object locators, version and registered artifact hashes. Report read-only objects according to host capabilities. Apply verified style changes to the same frozen data. Changes to scientific inputs or statistics require a new freeze. |
| Quality and assets | Host receipts distinguish generation, registration, editing and QA. | Ordinary SVG runs the necessary data, layout and format checks. PDF text and collision QA run on request against the exact exported bytes. PNG can stay internal. No system font, font redistribution, third-party demo asset or external model is required. The example uses licensed DejaVu Sans from the locked Matplotlib wheel. |

## Figure API and workbench

The owner-scoped routes below are implemented by `01_src/src/api/figure_router.py`. Paths are relative to `/api/v2/figures/projects/{figure_id}`.

| Method and path | Fixed-release behavior |
| --- | --- |
| `GET /preview.svg?v=` and `GET /preview.png?v=` | Serve authorized stored SVG or PNG preview bytes. |
| `GET` or `HEAD /export/{fmt}?v=` | Serve a registered format for the selected `render_version`. An absent format returns `404`. A stale `v` returns `409 revision_conflict`. |
| `POST /preview` and `POST /overrides` | Preview pending style edits or save a validated replay as a revision. Use `expected_revision` for edits. |
| `POST /export/{fmt}` at `36444ca` | Generate or reuse a registered PNG or PDF using body `{"expected_revision": <render_version>}`. Only a replay-capable project with an authorized registration session can generate a missing format. |
| `POST /verify` and `POST /bundle` | Verify authorized current stored bytes or bundle the existing artifact set. These endpoints do not run source or renderer scripts. |
| `POST /svg-edits` | Apply supported edits to a schematic SVG project. Matplotlib style replay uses `/overrides`. |

At `d275430`, the workbench (`01_src/web/assets/figures.js`) offers only formats already listed in `exports`. At `36444ca` it also offers `generatable_formats`. The POST uses the saved revision, renders the missing format through the host replay path, and registers the bytes with their hash and a revision-bound receipt. The workbench checks the receipt's figure, format, revision and file ID, then downloads via `/api/v2/files/{file_id}/download`. F04 still needs an installed-host check comparing independently hashed download bytes with `export.sha256` and the selected revision. An SVG-only project with saved replay evidence can use this action. An imported schematic SVG has no scientific replay path.

## Verification boundary

Independent CI checks Python 3.12 on GNU/Linux x86_64 with hash-locked dependencies, archive integrity, the synthetic standalone workflow and PDF QA. Comparing the entire vendor inventory to the pinned Git tree requires the separate upstream checkout. The synthetic tests cover the local equivalents of separate SVGs and composition, repair and partial success, optional PDF/PNG outputs, and geometry-preserving replay. Integrated F01–F05, actual model and Worker execution, account-scoped authorization, workbench downloads and edits, and visual or journal acceptance need evidence from the installed release.
