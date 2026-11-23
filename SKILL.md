---
name: nature-figure
description: Create, revise, and check data-driven manuscript figures with managed Python. Use for 论文配图, 科研绘图, publication plots, and scientific multi-panel figures. Use other workflows for dashboards, statistics-only analysis, or generated schematics.
---

# Nature figure

1. Identify the scientific question, variables, units, grouping keys and reader. Clarify missing decisions only when they change the figure or its interpretation. Use configured managed Python directly. If an explicitly required backend is unavailable, report the limitation.
2. Inspect the authorized attachment schema and read the complete selected data once. Keep raw points, keyed summaries and relevant source identity. Record missingness, exclusions, transformations and the definitions of statistics actually used. An ordinary attachment plot uses the supplied data and local compute.
3. Freeze the tables the renderer consumes. Render each independent figure from frozen DataFrames with a separate renderer that leaves one Figure and has stable object IDs. An explicitly requested scientific composition is one logical figure with multiple panels. See [figure design and templates](references/workflow.md).
4. Render, check and deliver one SVG per logical figure in order. Publish each verified SVG before starting the next. Preserve a successful result when a later figure fails. For a confirmed syntax or shape error, correct the cited portion and reuse unchanged inputs or frozen tables where valid. See [figure checks](references/quality.md).
5. Store the exact renderer and dependency versions, style parameters, frozen table identities, object IDs and output hash. Replay style changes against the same frozen tables and preserve the data geometry. For requested PDF submission checks, apply the target journal and stage requirements and state which checks ran. PNG can serve as an internal preview.

Use an available isolated execution capability with local inputs. Provisioning belongs to the managed environment. External generation, credential access, persistent backend preferences and automatic dependency installation are outside this workflow.

The [standalone example](scripts/grouped_example.py) uses [synthetic data](assets/groups.csv) for local preparation, sequential SVG delivery, replay and optional PDF QA.
