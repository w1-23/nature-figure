"""Run the standalone grouped-figure workflow with locally frozen data."""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from xml.etree import ElementTree

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from audits.audit_panel_alignment import PanelAlignmentError, require_matplotlib_panel_alignment
from freeze_groups import freeze_groups
from render_grouped import VIEW_TITLES, build_figure


SCRIPT_DIR = Path(__file__).resolve().parent
TABLE_TYPES = {
    "observations": {"group": "object", "value": "float64", "source_row": "int64", "position": "float64"},
    "summary": {"group": "object", "mean": "float64", "count": "int64", "order": "int64"},
}
SVG_NS = "{http://www.w3.org/2000/svg}"


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n").encode()


def freeze_csv(source, destination, *, expected_rows=None):
    raw = source.read_bytes()
    frame = pd.read_csv(io.BytesIO(raw), dtype={"group": str}, keep_default_na=False, float_precision="round_trip")
    tables = freeze_groups(frame, expected_rows=expected_rows)
    artifact = canonical({
        "version": 1, "input_sha256": digest(raw),
        "analysis_sha256": digest((SCRIPT_DIR / "freeze_groups.py").read_bytes()),
        "analysis_environment": {"numpy": np.__version__, "pandas": pd.__version__},
        "tables": {name: table.to_numpy().tolist() for name, table in tables.items()},
    })
    with tempfile.TemporaryDirectory(dir=destination.parent) as staging:
        temporary = Path(staging) / "frozen.json"
        temporary.write_bytes(artifact)
        os.link(temporary, destination)
    return {"frozen": str(destination), "sha256": digest(artifact), "rows": len(frame)}


def load_frozen(source):
    payload = source.read_bytes()
    frozen = json.loads(payload)
    if frozen.get("version") != 1 or set(frozen.get("tables", {})) != set(TABLE_TYPES):
        raise ValueError("Unsupported frozen grouped-figure data.")
    tables = {name: pd.DataFrame(frozen["tables"][name], columns=list(types)).astype(types)
              for name, types in TABLE_TYPES.items()}
    return frozen, tables, digest(payload)


def check_layout(figure):
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    canvas = figure.bbox

    def check_bounds(artists):
        boxes = [item.get_window_extent(renderer) for item in artists
                 if item.get_visible() and item.get_text()]
        for box in boxes:
            if not all(canvas.contains(*corner) for corner in (box.p0, box.p1)):
                raise ValueError("A rendered label falls outside the fixed canvas.")
        return boxes

    check_bounds(figure.texts)
    for axes in figure.axes:
        check_bounds([axes.xaxis.label, axes.yaxis.label, axes.title, *axes.texts,
                      axes.xaxis.get_offset_text(), axes.yaxis.get_offset_text()])
        legend = axes.get_legend()
        if legend is not None:
            check_bounds(legend.get_texts())
        for axis in (axes.xaxis, axes.yaxis):
            lower, upper = sorted(axis.get_view_interval())
            labels = [tick.label1 for tick in axis.get_major_ticks() if lower <= tick.get_loc() <= upper]
            boxes = check_bounds(labels)
            if any(box.overlaps(other) for index, box in enumerate(boxes) for other in boxes[index + 1:]):
                raise ValueError("Rendered tick labels overlap at the chosen canvas size.")
    return (require_matplotlib_panel_alignment(figure, require_panel_labels=True, strict=True)
            if len(figure.axes) > 1 else None)


def object_geometry(figure):
    objects = {}
    for axes in figure.axes:
        for series in axes.collections:
            objects[series.get_gid()] = series.get_offsets().tolist()
        for patch in axes.patches:
            objects[patch.get_gid()] = [float(value) for value in patch.get_bbox().bounds]
    return objects


def export(figure, destination, kind):
    with mpl.rc_context({"svg.fonttype": "path", "svg.hashsalt": "nature-figure",
                         "pdf.fonttype": 42, "pdf.use14corefonts": False, "savefig.bbox": None}):
        options = {"svg": {"metadata": {"Date": None}},
                   "pdf": {"metadata": {"CreationDate": None, "ModDate": None}},
                   "png": {"dpi": 144}}
        figure.savefig(destination, format=kind, **options[kind])
    data = destination.read_bytes()
    if kind == "svg":
        root = ElementTree.fromstring(data)
        href = "{http://www.w3.org/1999/xlink}href"
        if (root.tag != SVG_NS + "svg" or not root.get("viewBox")
                or any(node.tag in {SVG_NS + "image", SVG_NS + "script", SVG_NS + "foreignObject"}
                       or not node.get(href, node.get("href", "#")).startswith("#") for node in root.iter())):
            raise ValueError("Expected self-contained vector SVG with a fixed viewBox.")
    elif not data.startswith(b"%PDF-" if kind == "pdf" else b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"Invalid {kind} signature.")
    return {"file": destination.name, "bytes": len(data), "sha256": digest(data)}


def audit_pdf(path, *, minimum_pt):
    from audits.audit_figure_collisions import audit_pdf as audit_collisions
    from audits.audit_pdf_text import audit_pdf as audit_text

    text = audit_text(path.read_bytes(), minimum_pt)
    try:
        collisions = audit_collisions(path)
    except RuntimeError as exc:
        return {"status": "not_auditable", "text": text, "collision_error": str(exc)}
    collisions.pop("pdf", None)
    verdict = collisions["verdict"]
    if (text["auditable"] and text["below_minimum_count"]) or verdict == "FIX BEFORE DELIVERY":
        status = "fail"
    elif not text["auditable"] or verdict == "NOT AUDITABLE":
        status = "not_auditable"
    elif verdict == "REVIEW REQUIRED" or text["warnings"] or text["spacing_issue_count"]:
        status = "review_required"
    elif verdict == "PASS":
        status = "pass"
    else:
        status = "not_auditable"
    return {"status": status, "text": text, "collisions": collisions}


def publish_view(frozen, tables, frozen_sha, out, view, *, title=None, kind="svg", pdf_minimum_pt=None):
    if not view.isascii() or not view.isalpha():
        raise ValueError("A view name must contain only ASCII letters.")
    if pdf_minimum_pt is not None and (kind != "pdf" or not 0 < pdf_minimum_pt < float("inf")):
        raise ValueError("PDF text audit requires PDF and a positive finite minimum point size.")
    destination = out / view
    if destination.exists():
        raise FileExistsError(f"A result already exists for {view}. Select another output directory for revisions.")
    with tempfile.TemporaryDirectory(dir=out) as scratch:
        staging = Path(scratch) / "figure"
        staging.mkdir()
        figure = build_figure(tables, view=view, title=title)
        try:
            alignment = check_layout(figure)
            geometry = object_geometry(figure)
            path = staging / f"figure.{kind}"
            artifact = export(figure, path, kind)
            qa = {"status": "not_requested"} if pdf_minimum_pt is None else audit_pdf(path, minimum_pt=pdf_minimum_pt)
            receipt = {
                "view": view, "visibility": {"svg": "delivery", "png": "internal_preview", "pdf": "on_demand"}[kind],
                "artifact": artifact, "panels": len(figure.axes),
                "object_ids": sorted({item.get_gid() for item in figure.findobj() if item.get_gid()}),
                "style": {"title": VIEW_TITLES[view] if title is None else title},
                "geometry_sha256": digest(canonical(geometry)), "frozen_sha256": frozen_sha,
                "input_sha256": frozen["input_sha256"], "analysis_sha256": frozen["analysis_sha256"],
                "renderer_sha256": digest((SCRIPT_DIR / "render_grouped.py").read_bytes()),
                "runtime": {"python": sys.version.split()[0], "matplotlib": mpl.__version__,
                            "pandas": pd.__version__, "numpy": np.__version__},
                "svg_qa": {"status": "pass" if kind == "svg" else "not_requested", "panel_alignment": alignment},
                "visual_qa": "not_executed", "pdf_qa": qa,
            }
            (staging / "receipt.json").write_bytes(canonical(receipt))
            staging.rename(destination)
        finally:
            plt.close(figure)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("freeze")
    prepare.add_argument("csv", type=Path)
    prepare.add_argument("frozen", type=Path)
    prepare.add_argument("--expected-rows", type=int)
    render = commands.add_parser("render")
    render.add_argument("frozen", type=Path)
    render.add_argument("output_dir", type=Path)
    render.add_argument("views", nargs="+")
    render.add_argument("--title")
    render.add_argument("--format", choices=("svg", "pdf", "png"), default="svg")
    render.add_argument("--pdf-qa-min-pt", type=float)
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            print(json.dumps(freeze_csv(args.csv, args.frozen, expected_rows=args.expected_rows)), flush=True)
            return 0
        frozen, tables, sha = load_frozen(args.frozen)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        status = 0
        for view in args.views:
            receipt = publish_view(frozen, tables, sha, args.output_dir, view, title=args.title,
                                   kind=args.format, pdf_minimum_pt=args.pdf_qa_min_pt)
            print(json.dumps({"view": view, "receipt": str(args.output_dir / view / "receipt.json"),
                              "pdf_qa": receipt["pdf_qa"]["status"]}), flush=True)
            if receipt["pdf_qa"]["status"] in {"fail", "not_auditable", "review_required"}:
                status = 2
        return status
    except (OSError, ValueError, PanelAlignmentError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
