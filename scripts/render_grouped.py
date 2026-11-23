"""Build one Figure from frozen pandas DataFrames in a fresh Python namespace."""

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import ft2font
from matplotlib.font_manager import FontProperties
from matplotlib.text import Text
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd


VIEW_TITLES = {
    "observations": "Individual responses and group means",
    "means": "Mean response by group",
    "counts": "Observations per group",
    "combined": "Response and sample size by group",
}


def apply_package_font(figure):
    font_root = f"{mpl.get_data_path()}/fonts/ttf"
    fonts = {weight: f"{font_root}/{filename}" for weight, filename in
             (("normal", "DejaVuSans.ttf"), ("bold", "DejaVuSans-Bold.ttf"))}
    glyphs = {weight: ft2font.FT2Font(path).get_charmap() for weight, path in fonts.items()}
    for item in figure.findobj(Text):
        weight = "bold" if item.get_fontweight() == "bold" else "normal"
        if any(ord(char) not in glyphs[weight] for char in item.get_text() if not char.isspace()):
            raise ValueError("A label requires a glyph outside the managed DejaVu Sans font.")
        item.set_fontproperties(FontProperties(fname=fonts[weight], weight=weight, size=item.get_fontsize()))
        item.set_parse_math(False)


def _axes_labels(axes, summary, *, panel, ylabel):
    axes.set_gid(f"axes-{panel}")
    axes.set_xticks(summary["order"], summary["group"].tolist())
    axes.set_xlim(-0.5, len(summary) - 0.5)
    axes.set_xlabel("Group", gid=f"{panel}-xlabel")
    axes.set_ylabel(ylabel, gid=f"{panel}-ylabel")
    axes.tick_params(top=False, right=False)
    axes.spines[["right", "top"]].set_visible(False)


def _response(axes, summary, observations=None):
    _axes_labels(axes, summary, panel="response", ylabel="Response (a.u.)")
    if observations is not None:
        axes.scatter(observations["position"], observations["value"], s=19, alpha=0.73,
                     color="#0072B2", edgecolors="none", gid="response-points", label="Observations")
    axes.scatter(summary["order"], summary["mean"], s=35, marker="D", color="#9C3600",
                 linewidths=0.5, edgecolors="white", zorder=4, gid="response-means", label="Group mean")
    if observations is not None:
        axes.legend(loc="lower left", bbox_to_anchor=(0, 1.02), ncols=2, fontsize=7,
                    frameon=False, borderaxespad=0).set_gid("response-legend")


def _counts(axes, summary):
    _axes_labels(axes, summary, panel="count", ylabel="Number of observations")
    bars = axes.bar(summary["order"], summary["count"], width=0.58, color="#0072B2")
    for index, bar in enumerate(bars):
        bar.set_gid(f"count-bar-{index}")
    axes.set_ylim(bottom=0)
    axes.yaxis.set_major_locator(MaxNLocator(integer=True))


def build_figure(data, *, view="observations", title=None):
    if view not in VIEW_TITLES:
        raise ValueError(f"Unknown logical figure: {view!r}.")
    summary = data.get("summary")
    if not isinstance(summary, pd.DataFrame) or list(summary.columns) != ["group", "mean", "count", "order"]:
        raise ValueError("summary requires a frozen DataFrame with group,mean,count,order columns.")
    summary = summary.sort_values("order")
    if (summary.empty or not summary["group"].is_unique
            or summary["order"].tolist() != list(range(len(summary)))
            or not np.isfinite(summary["mean"]).all() or not (summary["count"] > 0).all()):
        raise ValueError("Frozen summaries require unique group keys, contiguous order, finite means and positive counts.")
    observations = None
    if view in {"observations", "combined"}:
        observations = data.get("observations")
        if not isinstance(observations, pd.DataFrame) or list(observations.columns) != ["group", "value", "source_row", "position"]:
            raise ValueError("observations requires a frozen DataFrame with group,value,source_row,position columns.")
        base = observations["group"].map(summary.set_index("group")["order"])
        if (observations.empty or base.isna().any() or set(observations["group"]) != set(summary["group"])
                or not np.isfinite(observations["value"]).all()
                or not (observations["position"].sub(base).abs() <= 0.11).all()):
            raise ValueError("Frozen raw points and display positions must agree with the summary group keys.")

    combined = view == "combined"
    with mpl.rc_context({"font.size": 8, "axes.linewidth": 0.65, "text.usetex": False,
                         "axes.formatter.use_mathtext": False, "figure.dpi": 100}):
        figure, axes = plt.subplots(1, 2 if combined else 1, squeeze=False,
                                    figsize=(7.09 if combined else 3.54, 2.56))
        try:
            figure.subplots_adjust(left=0.11 if combined else 0.21, right=0.97, bottom=0.22,
                                   top=0.70, wspace=0.48)
            panels = axes[0]
            if view == "counts":
                _counts(panels[0], summary)
            else:
                _response(panels[0], summary, observations)
            if combined:
                _counts(panels[1], summary)
                for label, panel in zip(("a", "b"), panels, strict=True):
                    panel.text(-0.11, 1.10, label, transform=panel.transAxes,
                               fontweight="bold", gid=f"panel-{label}")
            figure.suptitle(VIEW_TITLES[view] if title is None else title, fontsize=10,
                            y=0.95, gid="figure-title")
            for panel in panels:
                panel.get_xticklabels()
                panel.get_yticklabels()
            apply_package_font(figure)
            figure.canvas.draw()
            apply_package_font(figure)
        except Exception:
            plt.close(figure)
            raise
    return figure
