# nature-figure

An Agent Skills package for manuscript figures drawn with managed Python. See [SKILL.md](SKILL.md) for the SVG workflow and [CitrusScholar adapter](references/citrus-host-adapter.md) for host integration.

## GNU/Linux example

Use a provisioned CPython 3.12 environment. The hashed lock selects GNU/Linux x86_64 wheels. Provision dependencies as a maintainer. The plotting scripts do not install packages or access the network.

```bash
python -m pip install --require-hashes -r requirements.lock
out=$(mktemp -d)
python scripts/grouped_example.py freeze assets/groups.csv "$out/frozen.json" --expected-rows 9
python scripts/grouped_example.py render "$out/frozen.json" "$out/svg" observations means counts
```

Each SVG and receipt is available independently. See [workflow](references/workflow.md) for the explicit `combined` figure and replay. See [quality checks](references/quality.md) for the optional PDF audit. `requirements-pdf.lock` adds PyMuPDF. `requirements-dev.lock` adds auditing and inventory verification. With preloaded wheels, append `--no-index --find-links /path/to/wheels` to provision offline.

Verify with `python -m unittest discover -s tests -v` and `python tools/upstream_inventory.py ../upstream/nature-skills`. The inventory check runs offline once the checkout exists. See [NOTICE](NOTICE) and the [migration chart](MIGRATION.md) for licensing and changes.

The executable example covers grouped CSV with finite numeric observations and one two-panel composition. The SVG has outlined glyphs. Editable text, data and geometry remain available from the retained renderer and frozen tables. The shipped font supports a limited glyph repertoire. Actual journal compliance, visual inspection and integrated host acceptance are separate from the example's automated checks.
