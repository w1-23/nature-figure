# Figure design and templates

- Write one scientific claim or comparison per logical figure. Choose scatter and raw points for distributions, lines for measured trends, heatmaps for dense matrices, and a calibrated scale bar for imaging. Assign complementary roles to panels in an explicit composition.
- Choose the final physical size and consistent palette roles, ordering, units and repeated axes. Give categories a distinguishing encoding beyond color where possible. Avoid limits that drop observations or inconsistent scales that change interpretation. Measure layout after the final draw.
- Align raw values and summaries by group identifier. Keep a deterministic order and describe jitter as a display offset. Use defined intervals and denominators when they exist. Summaries and sample sizes do not imply hypothesis tests.
- In the caption explain each panel, abbreviations, experimental units, sample sizes and what the error marks represent. Supply the method behind any statistical or significance annotation.
- Use a licensed font supplied by the managed runtime and check glyph coverage. The example uses Matplotlib's DejaVu Sans and outlines SVG text. Preserve editable text via the renderer and project. Unsupported glyphs require a licensed managed font or an agreed alternative label.

[freeze_groups.py](../scripts/freeze_groups.py) retains every observation and row ordinal, freezes group means and counts, and computes deterministic display offsets. The [renderer](../scripts/render_grouped.py) aligns the frozen DataFrames by key and builds one Figure. A style edit can change title or color with the same tables and coordinates. New scientific computations produce a new frozen identity.

Other patterns can use the same separation. Freeze paired observations by subject and condition before drawing lines, calculated coordinates and thresholds for volcano and ROC plots, and explicit category order and values for marker dot plots. For matrices, document normalization, missing cells, row and column identities and color scale. The runnable example covers grouped data.

```bash
out=$(mktemp -d)
python scripts/grouped_example.py freeze assets/groups.csv "$out/frozen.json" --expected-rows 9
python scripts/grouped_example.py render "$out/frozen.json" "$out/delivery" observations means counts
python scripts/grouped_example.py render "$out/frozen.json" "$out/composition" combined
```

Each view emits its receipt when the SVG is available. A failed view has no new artifact. Continue from the same frozen data after correcting that view. Use a new output directory for a style replay with `--title`.
