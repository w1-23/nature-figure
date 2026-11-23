"""Prepare raw observations and keyed summaries for the grouped-plot example."""

import numpy as np
import pandas as pd


def freeze_groups(frame, *, expected_rows=None):
    if not isinstance(frame, pd.DataFrame) or list(frame.columns) != ["group", "value"]:
        raise ValueError("Input must be a DataFrame with exactly group,value columns in that order.")
    if expected_rows is not None and len(frame) != expected_rows:
        raise ValueError(f"FIGURE_FIXTURE_SHAPE: expected {expected_rows} observations, received {len(frame)}.")
    if frame.empty:
        raise ValueError("Input contains no observations.")
    labels = frame["group"]
    if not labels.map(lambda label: isinstance(label, str) and bool(label.strip())).all():
        raise ValueError("Each observation requires a nonempty string group.")
    values = pd.to_numeric(frame["value"], errors="raise").astype("float64")
    if not np.isfinite(values).all():
        raise ValueError("Each value must be finite. Resolve missing values explicitly before plotting.")

    observations = pd.DataFrame({
        "group": labels.to_numpy(), "value": values.to_numpy(),
        "source_row": np.arange(1, len(frame) + 1, dtype="int64"),
    })
    grouped = observations.groupby("group", sort=False)
    order = grouped.ngroup().astype("int64")
    size = grouped["value"].transform("size")
    rank = grouped.cumcount()
    offset = (0.20 * rank / (size - 1).clip(lower=1) - 0.10).where(size > 1, 0.0)
    observations["position"] = order + offset
    summary = grouped["value"].agg(mean="mean", count="size").reset_index()
    summary["order"] = np.arange(len(summary), dtype="int64")
    if not np.isfinite(summary["mean"]).all():
        raise ValueError("A group mean overflowed float64. Resolve numerical scaling before plotting.")
    return {"observations": observations, "summary": summary}
