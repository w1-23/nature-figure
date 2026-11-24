"""Fresh-namespace renderer and repair-replay contract for the standalone package.

The host executes a separated ``render_script`` through
``packages/citrus_figures/core.py::capture_outputs``. That path builds a fresh
global namespace (``__name__``, ``data``, ``plt``, ``matplotlib`` and
``show``) under ``matplotlib.rcParamsDefault``. Analysis locals, analysis
imports such as ``np``/``pd`` and the analysis ``emit`` helper are not carried
over. These fixtures pin that contract and replay one renderer failure through
a corrected renderer to a file-backed SVG receipt.
"""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "assets/groups.csv"
FIXTURES = ROOT / "tests"
sys.path.insert(0, str(ROOT / "scripts"))
import grouped_example as example
from freeze_groups import freeze_groups
from render_grouped import build_figure

SCRIPT = "<citrusfig>"
RENDERER = (ROOT / "scripts/render_grouped.py").read_text()
RENDERER_PREFIX = RENDERER if RENDERER.endswith("\n") else RENDERER + "\n"


def renderer_source(fixture):
    """A standalone custom renderer, as the model would submit it."""
    return (FIXTURES / fixture).read_text()


def shipped_renderer_source():
    """The shipped renderer plus its documented entry call."""
    return RENDERER_PREFIX + "fig = build_figure(data, view='observations')\n"


def script_error_line(error, filename=SCRIPT):
    """Mirror ``citrus_figures.core.script_error_line`` for the fixture runner."""
    if isinstance(error, SyntaxError) and error.filename == filename:
        return error.lineno
    trace, line = error.__traceback__, None
    while trace is not None:
        if trace.tb_frame.f_code.co_filename == filename:
            line = trace.tb_lineno
        trace = trace.tb_next
    return line


def render_scope(data):
    """Exactly the names the host supplies to a separated renderer."""
    return {
        "__name__": "__citrusfig__",
        "data": data,
        "plt": plt,
        "matplotlib": mpl,
        "show": lambda *args, **kwargs: None,
    }


def run_renderer(source, data, *, filename=SCRIPT):
    """Execute like ``capture_outputs``; return (figure, scope, error)."""
    plt.close("all")
    scope = render_scope(data)
    previous_show = plt.show
    plt.show = lambda *args, **kwargs: None
    try:
        with mpl.rc_context(rc=mpl.rcParamsDefault):
            exec(compile(source, filename, "exec"), scope)
        numbers = plt.get_fignums()
        if len(numbers) != 1:
            raise ValueError("A separated renderer must leave exactly one Figure.")
        return plt.figure(numbers[0]), scope, None
    except BaseException as exc:  # noqa: BLE001 - mirrors the host capture path
        plt.close("all")
        return None, scope, exc
    finally:
        plt.show = previous_show


class FreshRendererContractTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.scratch = Path(scratch.name)
        self.tables = freeze_groups(pd.read_csv(FIXTURE))

    def test_render_scope_supplies_only_documented_names(self):
        scope = render_scope(self.tables)
        self.assertEqual(set(scope), {"__name__", "data", "plt", "matplotlib", "show"})
        for absent in ("np", "numpy", "pd", "pandas", "emit", "load_dataset", "parameters"):
            self.assertNotIn(absent, scope)

    def test_analysis_imports_do_not_reach_the_renderer(self):
        analysis = {"__name__": "__citrusfig__"}
        exec("import numpy as np\nreference = np.zeros(2)", analysis)
        self.assertIn("np", analysis)

        figure, _scope, error = run_renderer(renderer_source("fresh-renderer-standalone-missing-np.py.txt"),
                                             self.tables)
        self.assertIsNone(figure)
        self.assertIsInstance(error, NameError)
        self.assertIn("np", str(error))

        fixture_lines = (FIXTURES / "fresh-renderer-standalone-missing-np.py.txt").read_text().splitlines()
        np_line = next(index for index, text in enumerate(fixture_lines, 1) if "np." in text)
        self.assertEqual(script_error_line(error), np_line)

        emit_figure, _scope, emit_error = run_renderer("emit.table('x', data['summary'])", self.tables)
        self.assertIsNone(emit_figure)
        self.assertIsInstance(emit_error, NameError)
        self.assertIn("emit", str(emit_error))

    def test_shipped_renderer_is_fresh_namespace_safe(self):
        figure, _scope, error = run_renderer(shipped_renderer_source(), self.tables)
        self.assertIsNone(error, msg=str(error))
        self.addCleanup(plt.close, figure)
        expected = build_figure(self.tables, view="observations")
        self.addCleanup(plt.close, expected)
        self.assertEqual(example.object_geometry(figure), example.object_geometry(expected))
        self.assertEqual([axes.get_gid() for axes in figure.axes],
                         [axes.get_gid() for axes in expected.axes])

    def test_self_import_and_pure_python_revisions_produce_the_same_line(self):
        imported, _scope, import_error = run_renderer(
            renderer_source("fresh-renderer-standalone-fixed-import.py.txt"), self.tables)
        self.assertIsNone(import_error, msg=str(import_error))
        self.addCleanup(plt.close, imported)
        pure, _scope, pure_error = run_renderer(
            renderer_source("fresh-renderer-standalone-fixed-pure.py.txt"), self.tables)
        self.assertIsNone(pure_error, msg=str(pure_error))
        self.addCleanup(plt.close, pure)
        np.testing.assert_allclose(imported.axes[0].lines[0].get_ydata(),
                                   pure.axes[0].lines[0].get_ydata())
        self.assertEqual(imported.axes[0].get_xlabel(), pure.axes[0].get_xlabel())
        self.assertEqual(imported.axes[0].get_ylabel(), pure.axes[0].get_ylabel())

    def test_missing_np_fails_then_fixed_renderer_registers_one_svg(self):
        frozen = self.scratch / "frozen.json"
        output = self.scratch / "delivery"
        with patch.object(pd, "read_csv", wraps=pd.read_csv) as read_csv:
            example.freeze_csv(FIXTURE, frozen)
            self.assertEqual(read_csv.call_count, 1)
        payload, tables, frozen_sha = example.load_frozen(frozen)

        figure, _scope, error = run_renderer(
            renderer_source("fresh-renderer-standalone-missing-np.py.txt"), tables)
        self.assertIsNone(figure)
        self.assertIsInstance(error, NameError)
        self.assertIsNotNone(script_error_line(error))
        self.assertFalse(output.exists())

        receipt = self.publish_fresh(payload, tables, frozen_sha, output, "observations",
                                     "fresh-renderer-standalone-fixed-import.py.txt")
        svg = output / "observations/figure.svg"
        data_bytes = svg.read_bytes()
        self.assertTrue(svg.is_file())
        self.assertGreater(len(data_bytes), 0)
        self.assertEqual(receipt["artifact"]["bytes"], len(data_bytes))
        self.assertEqual(receipt["artifact"]["sha256"], hashlib.sha256(data_bytes).hexdigest())
        self.assertEqual(receipt["frozen_sha256"], frozen_sha)
        self.assertEqual(receipt["input_sha256"], payload["input_sha256"])
        root = ElementTree.fromstring(data_bytes)
        self.assertEqual(root.tag, example.SVG_NS + "svg")
        self.assertTrue(root.get("viewBox"))
        self.assertTrue((output / "observations/receipt.json").is_file())
        self.assertNotIn("<svg", json.dumps(receipt))

    def publish_fresh(self, frozen, tables, frozen_sha, output, view, fixture):
        source = renderer_source(fixture)
        figure, _scope, error = run_renderer(source, tables)
        self.assertIsNone(error, msg=str(error))
        self.assertIsNotNone(figure)
        destination = output / view
        destination.mkdir(parents=True)
        try:
            svg = destination / "figure.svg"
            artifact = example.export(figure, svg, "svg")
            receipt = {
                "view": view,
                "visibility": "delivery",
                "artifact": artifact,
                "panels": len(figure.axes),
                "object_ids": sorted({item.get_gid() for item in figure.findobj() if item.get_gid()}),
                "geometry_sha256": example.digest(example.canonical(example.object_geometry(figure))),
                "frozen_sha256": frozen_sha,
                "input_sha256": frozen["input_sha256"],
                "analysis_sha256": frozen["analysis_sha256"],
                "renderer_sha256": example.digest(source.encode()),
                "svg_qa": {"status": "pass", "panel_alignment": None},
                "visual_qa": "not_executed",
                "pdf_qa": {"status": "not_requested"},
            }
            (destination / "receipt.json").write_bytes(example.canonical(receipt))
        finally:
            plt.close(figure)
        return receipt


if __name__ == "__main__":
    unittest.main()
