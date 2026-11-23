import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "assets/groups.csv"
sys.path.insert(0, str(ROOT / "scripts"))
import grouped_example as example
from freeze_groups import freeze_groups
from render_grouped import build_figure


class GroupedFigureTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.scratch = Path(scratch.name)
        self.frozen = self.scratch / "frozen.json"

    def test_shape_failure_and_repair(self):
        with self.assertRaisesRegex(ValueError, "expected 8 observations, received 9"):
            example.freeze_csv(FIXTURE, self.frozen, expected_rows=8)
        self.assertFalse(self.frozen.exists())
        result = example.freeze_csv(FIXTURE, self.frozen, expected_rows=9)
        self.assertEqual(result["rows"], 9)
        with self.assertRaises(FileExistsError):
            example.freeze_csv(FIXTURE, self.frozen)
        self.assertEqual(result["sha256"], hashlib.sha256(self.frozen.read_bytes()).hexdigest())

    def test_frozen_keys_survive_interleaved_input_and_shuffled_summary(self):
        frame = pd.read_csv(FIXTURE)
        tables = freeze_groups(frame)
        tables["summary"] = tables["summary"].sample(frac=1, random_state=0)
        figure = build_figure(tables)
        self.addCleanup(example.plt.close, figure)
        axes = figure.axes[0]
        self.assertEqual([label.get_text() for label in axes.get_xticklabels()], ["B", "C", "A"])
        points, means = axes.collections
        np.testing.assert_array_equal(points.get_offsets()[:, 1], frame["value"])
        np.testing.assert_array_equal(np.rint(points.get_offsets()[:, 0]), frame["group"].map({"B": 0, "C": 1, "A": 2}))
        np.testing.assert_array_equal(means.get_offsets(), [[0, 5], [1, 7], [2, 3]])
        self.assertEqual(Path(axes.xaxis.label.get_fontproperties().get_file()).name, "DejaVuSans.ttf")

    def test_fresh_renderer_syntax_repair_does_not_parse_or_aggregate(self):
        namespace = {"data": freeze_groups(pd.read_csv(FIXTURE))}
        renderer = (ROOT / "scripts/render_grouped.py").read_text()
        broken = (ROOT / "tests/invalid-renderer.py.txt").read_text()
        with self.assertRaises(SyntaxError):
            compile(renderer + "\n" + broken, "figure", "exec")
        live = set(example.plt.get_fignums())
        with patch.object(pd, "read_csv", side_effect=AssertionError("raw read during replay")), \
             patch.object(pd.DataFrame, "groupby", side_effect=AssertionError("aggregation during replay")):
            exec(compile(renderer + "\nfig = build_figure(data, view='means')\n", "figure", "exec"), namespace)
        figure = namespace["fig"]
        self.addCleanup(example.plt.close, figure)
        self.assertEqual(set(example.plt.get_fignums()) - live, {figure.number})
        self.assertNotIn("emit", namespace)

    def test_first_svg_exists_before_second_render_and_survives_failure(self):
        out = self.scratch / "output"
        with patch.object(pd, "read_csv", wraps=pd.read_csv) as read_csv:
            example.freeze_csv(FIXTURE, self.frozen)
            self.assertEqual(read_csv.call_count, 1)
        first = out / "observations/figure.svg"

        def fail_second(tables, *, view, title):
            if view == "means":
                self.assertTrue(first.is_file())
                raise ValueError("controlled second-view failure")
            return build_figure(tables, view=view, title=title)

        prefix = ["render", str(self.frozen), str(out)]
        log, errors = io.StringIO(), io.StringIO()
        with patch.object(pd, "read_csv", side_effect=AssertionError("duplicate CSV parse")), \
             contextlib.redirect_stdout(log), contextlib.redirect_stderr(errors):
            with patch.object(example, "build_figure", side_effect=fail_second):
                self.assertEqual(example.main(prefix + ["observations", "means", "counts"]), 2)
            self.assertIn("controlled second-view failure", errors.getvalue())
            self.assertFalse((out / "means").exists())
            earlier_bytes = first.read_bytes()
            self.assertEqual(example.main(prefix + ["means", "counts"]), 0)
        self.assertEqual([json.loads(line)["view"] for line in log.getvalue().splitlines()],
                         ["observations", "means", "counts"])
        self.assertEqual(first.read_bytes(), earlier_bytes)
        self.assertEqual(len(list(out.glob("*/figure.svg"))), 3)

    def render_view(self, directory, view, **kwargs):
        output = self.scratch / directory
        output.mkdir()
        return example.publish_view(*example.load_frozen(self.frozen), output, view, **kwargs)

    def test_composition_and_style_replay_keep_frozen_geometry(self):
        example.freeze_csv(FIXTURE, self.frozen)
        original = self.render_view("original", "combined")
        revised = self.render_view("revision", "combined", title="Revised title")
        self.assertEqual(original["panels"], 2)
        self.assertEqual(original["svg_qa"]["panel_alignment"]["verdict"], "PASS")
        for key in ("geometry_sha256", "frozen_sha256", "renderer_sha256", "object_ids"):
            self.assertEqual(original[key], revised[key])
        self.assertNotEqual(original["artifact"]["sha256"], revised["artifact"]["sha256"])
        self.assertEqual(original["pdf_qa"]["status"], "not_requested")

    @unittest.skipUnless(importlib.util.find_spec("pymupdf"), "optional PDF runtime is absent")
    def test_on_demand_pdf_and_internal_png_match_svg_geometry(self):
        example.freeze_csv(FIXTURE, self.frozen)
        svg = self.render_view("delivery", "means")
        pdf = self.render_view("audit", "means", kind="pdf", pdf_minimum_pt=5)
        png = self.render_view("preview", "means", kind="png")
        self.assertEqual(pdf["pdf_qa"]["status"], "pass")
        self.assertEqual(png["visibility"], "internal_preview")
        for key in ("geometry_sha256", "frozen_sha256"):
            self.assertEqual(svg[key], pdf[key])
            self.assertEqual(svg[key], png[key])

    def test_independent_host_loads_and_runs_installed_package(self):
        install = self.scratch / "skills/nature-figure"
        install.mkdir(parents=True)
        shutil.copy2(ROOT / "SKILL.md", install)
        for name in ("scripts", "references", "assets"):
            shutil.copytree(ROOT / name, install / name, ignore=shutil.ignore_patterns("__pycache__"))
        entry, = install.parent.glob("*/SKILL.md")
        _, frontmatter, instructions = entry.read_text().split("---\n", 2)
        meta = yaml.safe_load(frontmatter)
        self.assertEqual(meta["name"], install.name)
        self.assertLessEqual(len(meta["description"]), 1024)
        links = re.findall(r"\]\(([^)]+)\)", instructions)
        script, = [install / link for link in links if link.endswith(".py")]
        fixture, = [install / link for link in links if link.endswith(".csv")]
        for page in [entry, install / "references/workflow.md", install / "references/quality.md"]:
            for link in re.findall(r"\]\(([^)]+)\)", page.read_text()):
                path = (page.parent / link).resolve()
                self.assertTrue(path.is_relative_to(install) and path.is_file())
        source = Path(shutil.copy2(fixture, self.scratch / "input.csv"))
        env = {"PATH": os.defpath, "HOME": str(self.scratch), "MPLCONFIGDIR": str(self.scratch / "mpl")}
        command = [sys.executable, script]
        options = {"cwd": self.scratch, "env": env, "check": True, "capture_output": True, "timeout": 30}
        subprocess.run(command + ["freeze", source, self.frozen], **options)
        source.unlink()
        out = self.scratch / "output"
        run = subprocess.run(command + ["render", self.frozen, out, "observations", "means", "counts"], **options)
        self.assertEqual([json.loads(line)["view"] for line in run.stdout.splitlines()], ["observations", "means", "counts"])
        paths = list(out.glob("*/figure.svg"))
        self.assertEqual(len(paths), 3)
        for svg in paths:
            self.assertEqual(ElementTree.parse(svg).getroot().tag, example.SVG_NS + "svg")
            receipt = json.loads(svg.with_name("receipt.json").read_text())
            self.assertEqual(receipt["artifact"]["sha256"], hashlib.sha256(svg.read_bytes()).hexdigest())
