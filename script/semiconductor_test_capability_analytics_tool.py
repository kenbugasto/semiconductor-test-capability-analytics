#!/usr/bin/env python
# coding: utf-8

# # Semiconductor Test Capability Action Dashboard
# 
# This notebook generates a deterministic synthetic semiconductor test dataset and processes it through validation, lot-level capability analysis, daily/weekly/monthly summaries, IQR-filtered characterized-limit review, and an interactive HTML action dashboard.
# 
# For a production VCL workflow, replace the synthetic-data generation cell with the actual ZIP/CSV extraction and column-mapping stage while retaining the downstream analysis structure.
# 

# ## 1. Imports and configuration
# 
# Run this cell first. It defines the tester list, capability thresholds, and dashboard palette.
# 

# In[ ]:


"""Generate a synthetic semiconductor test dataset and an actionable HTML SPC report.

The project is intentionally designed as an interview-safe demonstration. It uses
synthetic names, limits, lots, testers, and measurements. No production data is used.
"""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 3611
TESTERS = ["TESTER_1", "TESTER_2", "TESTER_3", "TESTER_4"]

ANMYZ_GREEN = "#058247"
ANMYZ_BLUE = "#2C3E50"
ANMYZ_DARK_SLATE = "#34495E"
ANMYZ_MEDIUM_GRAY = "#7F8C8D"
ANMYZ_LIGHT_GRAY = "#BDC3C7"
ANMYZ_VERY_LIGHT_GRAY = "#ECF0F1"
ANMYZ_ORANGE = "#E56A54"
ANMYZ_YELLOW = "#FEDF58"
ANMYZ_RED = "#C94F3D"
ANMYZ_RANK_BLUE = "#4B6A88"
ANMYZ_VIOLET = "#8064A2"
ANMYZ_YELLOW_DARK = "#D4A900"
ANMYZ_LIGHT_GREEN = "#8BCF7A"
ANMYZ_LIGHT_BLUE = "#7DB7E8"
ANMYZ_GRID_COLOR = "#DDE3E6"
ANMYZ_BORDER_COLOR = "#BDC3C7"
CAPABILITY_BANDS = [
    (2.00, "QUALITY SCREEN"),
    (1.67, "PRODUCTION"),
    (1.33, "WARNING"),
    (-math.inf, "FAIL"),
]


# ## 2. Test specification generator
# 
# Creates 100 synthetic test parameters and their production-characterized LSL/USL values.
# 

# In[ ]:


def build_specifications() -> pd.DataFrame:
    """Create 100 synthetic test items with production-characterized limits."""
    families = [
        ("CONT_TEST_pin", 20, "CONT"),
        ("LEAK_TEST_pin", 20, "LEAK"),
        ("FUNC1_test_param", 20, "FUNC1"),
        ("FUNC2_test_param", 20, "FUNC2"),
        ("POST_CONT_TEST_pin", 10, "POST_CONT"),
        ("POST_LEAK_TEST_pin", 10, "POST_LEAK"),
    ]
    rows = []
    parameter_index = 0
    for prefix, count, family in families:
        for number in range(1, count + 1):
            parameter_index += 1
            if "LEAK" in family:
                target = 0.08 + number * 0.002
                nominal_sigma = 0.004
                unit = "uA"
            elif "CONT" in family:
                target = 0.45 + number * 0.012
                nominal_sigma = 0.012
                unit = "ohm"
            else:
                target = 10 + parameter_index * 0.17
                nominal_sigma = 0.18
                unit = "arb"
            half_width = nominal_sigma * 6.6
            rows.append(
                {
                    "parameter_index": parameter_index,
                    "test_item": f"{prefix}{number}",
                    "family": family,
                    "unit": unit,
                    "target": target,
                    "nominal_sigma": nominal_sigma,
                    "lsl": target - half_width,
                    "usl": target + half_width,
                    "limit_version": "SYNTH-V1",
                }
            )
    return pd.DataFrame(rows)


# ## 3. Synthetic measurement-level raw data
# 
# Creates 30 production days with multiple chronological lots, four testers, controlled drift/failure scenarios, and intentional validation issues. In your VCL version, this is the main section to replace with your actual extraction pipeline.
# 

# In[ ]:


def generate_measurements(specs: pd.DataFrame) -> pd.DataFrame:
    """Generate 30 production days with multiple chronological lots per day."""
    rng = np.random.default_rng(SEED)
    rows: list[dict] = []
    record_number = 0
    start = pd.Timestamp("2026-07-01 00:00:00")
    lot_order = 0

    for production_day in range(1, 31):
        day_start = start + pd.Timedelta(days=production_day - 1)
        # 15-25 units × 100 parameters produces 1.5k-2.5k valid records per day.
        tested_unit_count = int(rng.integers(15, 26))
        daily_lot_count = int(rng.integers(3, 6))
        unit_groups = np.array_split(np.arange(1, tested_unit_count + 1), daily_lot_count)

        for daily_lot_index, unit_group in enumerate(unit_groups, start=1):
            lot_order += 1
            lot_id = f"LOT-{lot_order:04d}"
            lot_hour = int(round((daily_lot_index - 0.5) * 24 / daily_lot_count))
            lot_start = day_start + pd.Timedelta(hours=min(lot_hour, 23))
            tester_assignments = [TESTERS[(unit - 1) % len(TESTERS)] for unit in unit_group]
            rng.shuffle(tester_assignments)

            for local_unit_index, (unit_number, tester) in enumerate(zip(unit_group, tester_assignments), start=1):
                event_time = lot_start + pd.Timedelta(minutes=local_unit_index)
                for spec in specs.itertuples(index=False):
                    record_number += 1
                    shift = 0.0
                    sigma_scale = 1.0
                    scenario = "BASELINE"

                    if spec.parameter_index <= 8 and production_day >= 12:
                        shift += spec.nominal_sigma * 0.22 * (production_day - 11)
                        scenario = "UPPER_DRIFT"
                    if 9 <= spec.parameter_index <= 14 and production_day >= 16:
                        shift -= spec.nominal_sigma * 0.25 * (production_day - 15)
                        scenario = "LOWER_DRIFT"
                    if 41 <= spec.parameter_index <= 46 and tester == "TESTER_4" and production_day >= 18:
                        shift += spec.nominal_sigma * 3.2
                        scenario = "TESTER_4_SHIFT"
                    if 61 <= spec.parameter_index <= 65 and production_day >= 20:
                        sigma_scale = 2.0
                        scenario = "VARIATION_INCREASE"
                    if 81 <= spec.parameter_index <= 85 and production_day in {24, 28, 30}:
                        shift += spec.nominal_sigma * 7.5
                        scenario = "SUDDEN_EXCURSION"

                    value = spec.target + shift + rng.normal(0, spec.nominal_sigma * sigma_scale)
                    rows.append(
                        {
                            "record_id": f"REC-{record_number:07d}",
                            "lot_id": lot_id,
                            "lot_order": lot_order,
                            "event_time": event_time,
                            "tester": tester,
                            "unit_id": f"U{unit_number:03d}",
                            "test_item": spec.test_item,
                            "family": spec.family,
                            "value": value,
                            "unit": spec.unit,
                            "lsl": spec.lsl,
                            "usl": spec.usl,
                            "scenario": scenario,
                            "validation_status": "VALID",
                        }
                    )

    data = pd.DataFrame(rows)

    # Intentional validation defects are retained for traceability and excluded from analysis.
    missing = data.sample(18, random_state=11).copy()
    missing["record_id"] = [f"BAD-MISSING-{i:03d}" for i in range(1, 19)]
    missing["value"] = np.nan
    missing["validation_status"] = "MISSING_VALUE"

    duplicates = data.sample(12, random_state=22).copy()
    duplicates["validation_status"] = "DUPLICATE_RECORD"

    invalid_tester = data.sample(8, random_state=33).copy()
    invalid_tester["record_id"] = [f"BAD-TESTER-{i:03d}" for i in range(1, 9)]
    invalid_tester["tester"] = "TESTER_9"
    invalid_tester["validation_status"] = "INVALID_TESTER"

    return pd.concat([data, missing, duplicates, invalid_tester], ignore_index=True)


# ## 4. Capability and period calculations
# 
# Calculates descriptive statistics, Cpu, Cpl, Cpk, capability classification, lot ranking, daily/weekly/monthly summaries, and IQR-filtered sigma recommendations.
# 

# In[ ]:


def capability_status(cpk: float | None) -> str:
    if cpk is None or pd.isna(cpk):
        return "REVIEW"
    for threshold, label in CAPABILITY_BANDS:
        if cpk >= threshold:
            return label
    return "FAIL"


def unique_mode(series: pd.Series) -> float | None:
    rounded = series.round(6)
    counts = rounded.value_counts()
    if counts.empty or counts.iloc[0] <= 1:
        return None
    return float(counts.index[0])


def summarize_group(group: pd.DataFrame) -> pd.Series:
    values = group["value"].dropna()
    mean = values.mean()
    stdev = values.std(ddof=1)
    lsl = group["lsl"].iloc[0]
    usl = group["usl"].iloc[0]
    if pd.isna(stdev) or stdev <= 0:
        cpu = cpl = cpk = np.nan
    else:
        cpu = (usl - mean) / (3 * stdev)
        cpl = (mean - lsl) / (3 * stdev)
        cpk = min(cpu, cpl)
    return pd.Series(
        {
            "sample_count": len(values),
            "mean": mean,
            "median": values.median(),
            "mode": unique_mode(values),
            "minimum": values.min(),
            "maximum": values.max(),
            "stdev": stdev,
            "q1": values.quantile(0.25),
            "q3": values.quantile(0.75),
            "lsl": lsl,
            "usl": usl,
            "cpu": cpu,
            "cpl": cpl,
            "cpk": cpk,
            "out_of_spec_count": int(((values < lsl) | (values > usl)).sum()),
        }
    )


def build_lot_summary(valid: pd.DataFrame) -> pd.DataFrame:
    summary = (
        valid.groupby(["lot_id", "lot_order", "test_item", "family"], sort=False)
        .apply(summarize_group, include_groups=False)
        .reset_index()
    )
    lot_times = valid.groupby("lot_id")["event_time"].max()
    scenarios = valid.groupby(["lot_id", "test_item"])["scenario"].agg(
        lambda x: ", ".join(sorted(set(x) - {"BASELINE"})) or "BASELINE"
    )
    summary["event_time"] = summary["lot_id"].map(lot_times)
    summary["scenario"] = [scenarios.loc[(lot, item)] for lot, item in zip(summary["lot_id"], summary["test_item"])]
    summary["capability_status"] = summary["cpk"].map(capability_status)
    summary["cpk_rank"] = summary.groupby("lot_id")["cpk"].rank(method="first", ascending=True)
    summary["bottom_20_percent"] = summary["cpk_rank"] <= 20
    summary["required_action"] = summary["capability_status"].map(
        {
            "FAIL": "Hold lot and investigate parameter/tester",
            "WARNING": "Review drift and marginality before release",
            "PRODUCTION": "Continue production monitoring",
            "QUALITY SCREEN": "No immediate action",
            "REVIEW": "Resolve missing capability inputs",
        }
    )
    return summary.sort_values(["lot_order", "cpk"], na_position="first")


def build_period_summary(valid: pd.DataFrame) -> pd.DataFrame:
    frames = []
    keyed = valid.copy()
    keyed["DAILY"] = keyed["event_time"].dt.strftime("%Y-%m-%d")
    keyed["WEEKLY"] = keyed["event_time"].dt.strftime("%G-W%V")
    keyed["MONTHLY"] = keyed["event_time"].dt.strftime("%Y-%m")
    for period_type in ["DAILY", "WEEKLY", "MONTHLY"]:
        result = (
            keyed.groupby([period_type, "test_item", "family"], sort=False)
            .apply(summarize_group, include_groups=False)
            .reset_index()
            .rename(columns={period_type: "period"})
        )
        result.insert(0, "period_type", period_type)
        result["capability_status"] = result["cpk"].map(capability_status)
        frames.append(result)
    return pd.concat(frames, ignore_index=True)


def build_monthly_recommendations(valid: pd.DataFrame) -> pd.DataFrame:
    data = valid.copy()
    data["month"] = data["event_time"].dt.strftime("%Y-%m")
    rows = []
    for (month, test_item, family), group in data.groupby(["month", "test_item", "family"]):
        values = group["value"].dropna()
        q1, q3 = values.quantile([0.25, 0.75])
        iqr = q3 - q1
        filtered = values[(values >= q1 - 1.5 * iqr) & (values <= q3 + 1.5 * iqr)]
        mean, stdev = filtered.mean(), filtered.std(ddof=1)
        row = {
            "month": month,
            "test_item": test_item,
            "family": family,
            "raw_count": len(values),
            "iqr_filtered_count": len(filtered),
            "IQR_removed_outliers": len(values) - len(filtered),
            "removed_percent": (len(values) - len(filtered)) / len(values),
            "filtered_mean": mean,
            "filtered_stdev": stdev,
            "current_lsl": group["lsl"].iloc[0],
            "current_usl": group["usl"].iloc[0],
        }
        for sigma in [3, 4, 5, 6]:
            row[f"proposed_{sigma}s_lsl"] = mean - sigma * stdev
            row[f"proposed_{sigma}s_usl"] = mean + sigma * stdev
        row["remarks"] = "FOR ENGG REVIEW"
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["month", "test_item"])


# ## 5. Output and plotting helpers
# 
# Formats HTML tables and Plotly figures and writes the categorized cleaned-record workbook.
# 

# In[ ]:


def dataframe_html(df: pd.DataFrame, columns: list[str], max_rows: int | None = None) -> str:
    view = df.loc[:, columns].copy()
    if max_rows is not None:
        view = view.head(max_rows)
    numeric = view.select_dtypes(include="number").columns
    view[numeric] = view[numeric].round(4)
    return view.to_html(index=False, border=0, classes="data-table", na_rep="—", escape=True)


def plot_div(div_id: str, traces: list[dict], layout: dict) -> str:
    layout = {
        "paper_bgcolor": "#EEEEEE",
        "plot_bgcolor": "#FFFFFF",
        "font": {"color": ANMYZ_BLUE},
        "hoverlabel": {"bgcolor": "#FFFFFF", "font": {"color": "#000000"}, "bordercolor": ANMYZ_BORDER_COLOR if "ANMYZ_BORDER_COLOR" in globals() else ANMYZ_LIGHT_GRAY},
        "xaxis": {"gridcolor": ANMYZ_GRID_COLOR},
        "yaxis": {"gridcolor": ANMYZ_GRID_COLOR},
        **layout,
    }
    return (
        f'<div id="{html.escape(div_id)}" class="plot"></div>'
        f'<script>Plotly.newPlot({json.dumps(div_id)}, {json.dumps(traces)}, '
        f'{json.dumps(layout)}, {{responsive:true, displaylogo:false}});</script>'
    )


def write_cleaned_records_log(raw: pd.DataFrame, output_path: Path) -> None:
    """Write one worksheet per rejected-record category for easy source correction."""
    issues = raw[raw["validation_status"] != "VALID"].copy()
    sheet_map = {
        "MISSING_VALUE": "Missing Values",
        "DUPLICATE_RECORD": "Duplicates",
        "INVALID_TESTER": "Invalid Tester",
    }
    with pd.ExcelWriter(output_path, engine="xlsxwriter", datetime_format="yyyy-mm-dd hh:mm:ss") as writer:
        summary = (
            issues["validation_status"]
            .value_counts()
            .rename_axis("cleaned_record_category")
            .reset_index(name="record_count")
        )
        summary.to_excel(writer, sheet_name="Summary", index=False)
        for status, sheet_name in sheet_map.items():
            issues.loc[issues["validation_status"] == status].to_excel(writer, sheet_name=sheet_name, index=False)
        workbook = writer.book
        header = workbook.add_format({"bold": True, "font_color": "white", "bg_color": ANMYZ_BLUE, "border": 0})
        for worksheet in writer.sheets.values():
            worksheet.freeze_panes(1, 0)
            worksheet.autofilter(0, 0, worksheet.dim_rowmax, worksheet.dim_colmax)
            worksheet.set_row(0, 22, header)
            worksheet.set_column(0, worksheet.dim_colmax, 18)


# ## 6. Interactive HTML report builder
# 
# Builds the KPI cards, extraction pipeline, immediate action list, capability drift selector, failing-parameter diagnostics, and monthly limit-review table.
# 

# In[ ]:


def build_html_report(
    raw: pd.DataFrame,
    valid: pd.DataFrame,
    lot_summary: pd.DataFrame,
    period_summary: pd.DataFrame,
    recommendations: pd.DataFrame,
    extraction_manifest: pd.DataFrame,
    output_path: Path,
) -> None:
    previous_day = (pd.to_datetime(extraction_manifest["extraction_date"].max()) - pd.Timedelta(days=1)).date()
    previous_day_valid = valid[valid["event_time"].dt.date == previous_day].copy()
    latest = (
        previous_day_valid.groupby(["test_item", "family"], sort=False)
        .apply(summarize_group, include_groups=False)
        .reset_index()
        .sort_values("cpk")
    )
    scenarios = previous_day_valid.groupby("test_item")["scenario"].agg(
        lambda x: ", ".join(sorted(set(x) - {"BASELINE"})) or "BASELINE"
    )
    latest["scenario"] = latest["test_item"].map(scenarios)
    latest["capability_status"] = latest["cpk"].map(capability_status)
    latest["cpk_rank"] = latest["cpk"].rank(method="first", ascending=True).astype(int)
    latest["required_action"] = latest["capability_status"].map(
        {"FAIL": "Hold lots and investigate parameter/tester", "WARNING": "Review drift and marginality before release", "PRODUCTION": "Continue production monitoring", "QUALITY SCREEN": "No immediate action", "REVIEW": "Resolve missing capability inputs"}
    )
    status_counts = latest["capability_status"].value_counts().reindex(
        ["FAIL", "WARNING", "PRODUCTION", "QUALITY SCREEN"], fill_value=0
    )
    fail_rows = latest[latest["capability_status"] == "FAIL"]
    warning_rows = latest[latest["capability_status"] == "WARNING"]
    overall_status = "FAIL - HOLD" if not fail_rows.empty else "WARNING - REVIEW" if not warning_rows.empty else "PASS"
    validation = raw["validation_status"].value_counts()

    status_y_max = int(status_counts.max()) + 10
    status_labels = [
        "FAIL (Cpk < 1.33)",
        "WARNING (1.33 ≤ Cpk < 1.67)",
        "PRODUCTION (1.67 ≤ Cpk < 2.00)",
        "QUALITY SCREEN (Cpk ≥ 2.00)",
    ]
    status_plot = plot_div(
        "status-plot",
        [{
            "type": "bar",
            "x": status_labels,
            "y": status_counts.tolist(),
            "marker": {"color": [ANMYZ_ORANGE, ANMYZ_YELLOW, ANMYZ_BLUE, ANMYZ_GREEN]},
            "text": status_counts.tolist(),
            "textposition": "outside",
            "hovertemplate": "📊 Status=%{x}<br>🔢 Parameters=%{y}<extra></extra>",
        }],
        {"title": f"📊 Previous Day ({previous_day}) Cpk Analysis", "height": 380, "margin": {"t": 60, "r": 25, "b": 115, "l": 50}, "xaxis": {"tickangle": -15, "gridcolor": ANMYZ_GRID_COLOR}, "yaxis": {"title": "Test parameters", "gridcolor": ANMYZ_GRID_COLOR, "range": [0, status_y_max]}},
    )

    validation_issues = validation.drop(labels=["VALID"], errors="ignore")
    validation_y_max = int(validation_issues.max()) + 10
    validation_plot = plot_div(
        "validation-plot",
        [{"type": "bar", "x": validation_issues.index.tolist(), "y": validation_issues.tolist(), "marker": {"color": [ANMYZ_ORANGE, ANMYZ_RANK_BLUE, ANMYZ_VIOLET]}, "text": validation_issues.tolist(), "textposition": "outside", "hovertemplate": "🧹 Category=%{x}<br>🔢 Records=%{y}<extra></extra>"}],
        {"title": "🧹 Cleaned Data Records", "height": 340, "margin": {"t": 60, "r": 25, "b": 80, "l": 50}, "yaxis": {"title": "Records", "gridcolor": ANMYZ_GRID_COLOR, "range": [0, validation_y_max]}},
    )

    manifest_plot = plot_div(
        "daily-extraction-plot",
        [
            {"type": "bar", "name": "Valid records", "x": extraction_manifest["extraction_date"].astype(str).tolist(), "y": extraction_manifest["valid_records"].tolist(), "marker": {"color": ANMYZ_BLUE}, "opacity": 0.7, "hovertemplate": "📅 Date=%{x}<br>✅ Valid records=%{y}<extra></extra>"},
            {"type": "scatter", "mode": "lines+markers", "name": "Data validation issues", "x": extraction_manifest["extraction_date"].astype(str).tolist(), "y": extraction_manifest["validation_issues"].tolist(), "yaxis": "y2", "line": {"color": ANMYZ_ORANGE, "width": 2}, "marker": {"color": ANMYZ_ORANGE}, "hovertemplate": "📅 Date=%{x}<br>⚠️ Issues=%{y}<extra></extra>"},
        ],
        {"title": "⚙️ Daily Extraction Pipeline", "height": 390, "margin": {"t": 60, "r": 70, "b": 65, "l": 70}, "xaxis": {"title": "Scheduled extraction date", "gridcolor": ANMYZ_GRID_COLOR}, "yaxis": {"title": "Valid records", "gridcolor": ANMYZ_GRID_COLOR}, "yaxis2": {"title": "Issues", "overlaying": "y", "side": "right", "rangemode": "tozero", "gridcolor": ANMYZ_GRID_COLOR}, "legend": {"orientation": "h", "y": 1.14}},
    )

    diagnostics = []
    for row in fail_rows.itertuples(index=False):
        detail = previous_day_valid[previous_day_valid["test_item"] == row.test_item].sort_values("event_time")
        lot_times = detail.groupby("lot_id")["event_time"].min().sort_values()
        day_start = pd.Timestamp(previous_day)
        day_end = day_start + pd.Timedelta(days=1)
        lot_traces = []
        for lot_index, (lot, timestamp) in enumerate(lot_times.items()):
            lot_data = detail[detail["lot_id"] == lot]
            lot_traces.append({"type": "box", "name": lot, "x": [timestamp.isoformat()] * len(lot_data), "y": lot_data["value"].round(8).tolist(), "boxpoints": "all", "jitter": 0.2, "marker": {"color": [ANMYZ_BLUE, ANMYZ_GREEN, ANMYZ_LIGHT_BLUE, ANMYZ_VIOLET][lot_index % 4], "size": 5}, "line": {"color": [ANMYZ_BLUE, ANMYZ_GREEN, ANMYZ_LIGHT_BLUE, ANMYZ_VIOLET][lot_index % 4]}, "hovertemplate": "📦 Lot=%{fullData.name}<br>🕒 Event time=%{x|%H:%M}<br>📏 Value=%{y}<extra></extra>"})
        lot_traces.extend([
            {"type": "scatter", "mode": "lines", "name": "USL", "x": [day_start.isoformat(), day_end.isoformat()], "y": [row.usl, row.usl], "line": {"color": ANMYZ_RED, "dash": "dash"}, "hovertemplate": "🔺 USL=%{y}<extra></extra>"},
            {"type": "scatter", "mode": "lines", "name": "LSL", "x": [day_start.isoformat(), day_end.isoformat()], "y": [row.lsl, row.lsl], "line": {"color": ANMYZ_RED, "dash": "dash"}, "hovertemplate": "🔻 LSL=%{y}<extra></extra>"},
        ])
        lot_box = plot_div(
            f"lot-box-{row.cpk_rank:.0f}", lot_traces,
            {"title": {"text": f"📦 {row.test_item}: Previous-Day Distribution by Lot", "y": 0.98}, "height": 430, "margin": {"t": 115, "r": 25, "b": 80, "l": 70}, "xaxis": {"title": "Previous-day event time (3-hour divisions)", "type": "date", "tickformat": "%H:%M", "dtick": 10800000, "range": [day_start.isoformat(), day_end.isoformat()], "showgrid": True, "gridcolor": ANMYZ_GRID_COLOR}, "yaxis": {"title": f"Value ({detail['unit'].iloc[0]})", "gridcolor": ANMYZ_GRID_COLOR}, "legend": {"orientation": "h", "x": 0, "y": 1.10, "yanchor": "bottom"}},
        )
        tester_colors = [ANMYZ_BLUE, ANMYZ_GREEN, ANMYZ_LIGHT_BLUE, ANMYZ_VIOLET]
        box_traces = [
            {"type": "box", "name": tester, "y": detail.loc[detail["tester"] == tester, "value"].round(8).tolist(), "boxpoints": "all", "jitter": 0.25, "marker": {"color": tester_colors[index]}, "line": {"color": tester_colors[index]}, "hovertemplate": "🧪 Tester=%{fullData.name}<br>📏 Value=%{y}<extra></extra>"}
            for index, tester in enumerate(TESTERS)
        ]
        box_traces.append({"type": "scatter", "mode": "lines", "name": "USL", "x": TESTERS, "y": [row.usl] * len(TESTERS), "line": {"color": ANMYZ_RED, "dash": "dash"}, "hovertemplate": "🔺 USL=%{y}<extra></extra>"})
        value_min, value_max = detail["value"].min(), detail["value"].max()
        span = max(value_max - value_min, abs(row.usl) * 0.01, 1e-9)
        zoom_range = [value_min - 0.05 * span, max(value_max, row.usl) + 0.05 * span]
        box = plot_div(
            f"box-{row.cpk_rank:.0f}",
            box_traces,
            {"title": {"text": f"🧪 {row.test_item}: Distribution by Tester", "y": 0.98}, "height": 430, "margin": {"t": 115, "r": 25, "b": 65, "l": 70}, "yaxis": {"title": f"Value ({detail['unit'].iloc[0]})", "gridcolor": ANMYZ_GRID_COLOR, "range": zoom_range}, "showlegend": True, "legend": {"orientation": "h", "x": 0, "y": 1.10, "yanchor": "bottom"}},
        )
        diagnostics.append(
            f"""
            <details class="diagnostic" {'open' if len(diagnostics) < 2 else ''}>
              <summary><span class="fail-pill">FAIL</span> {html.escape(row.test_item)} · Cpk {row.cpk:.3f} · {html.escape(row.scenario)}</summary>
              <div class="metric-strip">
                <span>Mean <b>{row.mean:.4f}</b></span><span>Stdev <b>{row.stdev:.4f}</b></span>
                <span>Cpu <b>{row.cpu:.3f}</b></span><span>Cpl <b>{row.cpl:.3f}</b></span>
                <span>LSL <b>{row.lsl:.4f}</b></span><span>USL <b>{row.usl:.4f}</b></span>
              </div>
              <div class="plot-grid">{lot_box}{box}</div>
            </details>
            """
        )

    worst_items = fail_rows["test_item"].tolist()
    trend_traces = []
    trend_colors = [ANMYZ_BLUE, ANMYZ_GREEN, ANMYZ_RANK_BLUE, ANMYZ_VIOLET]
    for item_index, item in enumerate(worst_items):
        item_data = lot_summary[lot_summary["test_item"] == item].sort_values("lot_order")
        color = trend_colors[item_index % len(trend_colors)]
        trend_traces.append({"type": "scatter", "mode": "lines+markers", "name": item, "x": item_data["event_time"].astype(str).tolist(), "y": item_data["cpk"].round(4).tolist(), "visible": item_index == 0, "line": {"color": color, "width": 3}, "marker": {"color": color}, "hovertemplate": "🧪 Test item=%{fullData.name}<br>🕒 Time=%{x}<br>📈 Cpk=%{y}<extra></extra>"})
    trend_traces.extend(
        [
            {"type": "scatter", "mode": "lines", "name": "Fail 1.33", "x": [str(lot_summary["event_time"].min()), str(lot_summary["event_time"].max())], "y": [1.33, 1.33], "line": {"color": ANMYZ_RED, "dash": "dash"}, "hovertemplate": "🛑 Fail threshold=1.33<extra></extra>"},
            {"type": "scatter", "mode": "lines", "name": "Production 1.67", "x": [str(lot_summary["event_time"].min()), str(lot_summary["event_time"].max())], "y": [1.67, 1.67], "line": {"color": "#000000", "dash": "dot"}, "hovertemplate": "🏭 Production threshold=1.67<extra></extra>"},
            {"type": "scatter", "mode": "lines", "name": "Quality 2.00", "x": [str(lot_summary["event_time"].min()), str(lot_summary["event_time"].max())], "y": [2.0, 2.0], "line": {"color": ANMYZ_GREEN, "dash": "dot"}, "hovertemplate": "✅ Quality threshold=2.00<extra></extra>"},
        ]
    )
    trend_buttons = []
    for item_index, item in enumerate(worst_items):
        visible = [index == item_index for index in range(len(worst_items))] + [True, True, True]
        trend_buttons.append({"label": item, "method": "update", "args": [{"visible": visible}, {"title": f"📈 Capability Drift — {item}"}]})
    trend_plot = plot_div(
        "cpk-trend",
        trend_traces,
        {"title": f"📈 Capability Drift — {worst_items[0]}", "height": 460, "margin": {"t": 90, "r": 25, "b": 65, "l": 70}, "xaxis": {"title": "Lot event time", "gridcolor": ANMYZ_GRID_COLOR}, "yaxis": {"title": "Cpk", "gridcolor": ANMYZ_GRID_COLOR}, "legend": {"orientation": "h", "y": 1.15}, "updatemenus": [{"buttons": trend_buttons, "direction": "down", "showactive": True, "x": 0, "xanchor": "left", "y": 1.28, "yanchor": "top", "bgcolor": "#FFFFFF", "bordercolor": ANMYZ_BORDER_COLOR}]},
    )

    priority_columns = ["cpk_rank", "test_item", "family", "cpk", "cpu", "cpl", "mean", "lsl", "usl", "scenario", "required_action"]
    action_view = pd.concat([fail_rows, warning_rows]).sort_values("cpk").copy()
    action_view["cpk_rank"] = action_view["cpk_rank"].astype(int)
    latest_month = recommendations["month"].max()
    rec_view = recommendations[recommendations["month"] == latest_month].copy()
    rec_view["limit_change_6s"] = (rec_view["proposed_6s_usl"] - rec_view["proposed_6s_lsl"]) - (rec_view["current_usl"] - rec_view["current_lsl"])
    rec_view = rec_view.reindex(rec_view["limit_change_6s"].abs().sort_values(ascending=False).index)

    css = """
    :root{--navy:#2C3E50;--blue:#2C3E50;--red:#C94F3D;--orange:#E56A54;--yellow:#FEDF58;--green:#058247;--bg:#EEEEEE;--line:#BDC3C7}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:#2C3E50;font:14px Arial,sans-serif}.wrap{max-width:1500px;margin:auto;padding:28px}
    h1{margin:0;color:var(--navy);font-size:30px}h2{color:var(--navy);margin-top:34px}.subtitle{color:#667085;margin:7px 0 24px}.alert{padding:16px 20px;border-left:6px solid var(--red);background:#fff1f0;color:#8b1e16;font-size:18px;font-weight:700;margin-bottom:20px}
    .cards{display:grid;grid-template-columns:repeat(5,minmax(150px,1fr));gap:14px}.card{background:#E2E7E9;border:1px solid var(--line);border-radius:10px;padding:16px;color:var(--navy)}.card.fail{background:#F0AAA0}.card.warn{background:#FFE88F}.card.good{background:#96D2B3}.card .label{font-size:12px;text-transform:uppercase;color:inherit}.card .value{font-size:26px;font-weight:700;margin-top:7px;color:inherit}
    .panel{background:white;border:1px solid var(--line);border-radius:10px;padding:16px;margin:16px 0}.two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px}.plot{width:100%;min-height:300px}
    .data-table{border-collapse:collapse;width:100%;font-size:12px}.data-table th{background:var(--navy);color:#fff;padding:9px}.data-table td{border-bottom:1px solid #e7ebf0;padding:7px;text-align:right}.data-table td:nth-child(2),.data-table td:nth-last-child(1){text-align:left}.table-scroll{max-height:420px;overflow:auto}.immediate-actions .data-table td:nth-child(4){color:#C94F3D;font-weight:700}.table-details{background:#fff;border:1px solid var(--line);border-radius:10px;margin:16px 0;padding:0 14px}.table-details>summary{padding:16px 4px}.table-details .table-scroll{padding:0 0 16px}
    details.diagnostic{background:#fff;border:1px solid var(--line);border-radius:9px;margin:12px 0;padding:0 14px}details summary{cursor:pointer;padding:16px 4px;font-weight:700;color:var(--navy)}.fail-pill{background:var(--red);color:white;border-radius:12px;padding:4px 8px;font-size:11px;margin-right:8px}.metric-strip{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 8px}.metric-strip span{background:#f0f3f8;border-radius:6px;padding:8px 10px}.plot-grid{display:grid;grid-template-columns:1.3fr 1fr;gap:10px}
    .note{background:#fff8e1;border-left:4px solid var(--yellow);padding:12px 16px;color:#5f4b00}.footer{color:#667085;font-size:12px;margin:32px 0 8px}
    @media(max-width:900px){.cards{grid-template-columns:1fr 1fr}.two-col,.plot-grid{grid-template-columns:1fr}.wrap{padding:16px}}
    """

    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Semiconductor Test Capability Action Dashboard</title><script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script><style>{css}</style></head>
<body><main class="wrap">
<h1>🧪 Semiconductor Test Capability Action Dashboard</h1>
<p class="subtitle">Synthetic production-test demonstration · Previous day {previous_day} · {previous_day_valid['lot_id'].nunique()} chronological lots · 100 characterized test parameters</p>
<div class="alert">{overall_status}: {len(fail_rows)} parameters failed capability screening and require immediate engineering review.</div>
<section class="cards">
  <div class="card fail"><div class="label">Overall status</div><div class="value">{overall_status}</div></div>
  <div class="card fail"><div class="label">Fail parameters</div><div class="value">{len(fail_rows)}</div></div>
  <div class="card warn"><div class="label">Warning parameters</div><div class="value">{len(warning_rows)}</div></div>
  <div class="card good"><div class="label">Valid measurements</div><div class="value">{len(valid):,}</div></div>
  <div class="card"><div class="label">Data validation issues</div><div class="value">{int(validation_issues.sum())}</div></div>
</section>
<section class="two-col"><div class="panel">{validation_plot}</div><div class="panel">{status_plot}</div></section>
<h2>⚙️ Daily Extraction Pipeline</h2><p class="note">The scheduled batch extracts completed production records each day, validates and appends them to the historical dataset, and refreshes daily, ISO-weekly, and monthly capability summaries.</p>
<div class="panel">{manifest_plot}</div>
<details class="table-details"><summary>📋 View Daily Extraction Summary</summary><div class="table-scroll">{dataframe_html(extraction_manifest, ['extraction_date','source_records','valid_records','validation_issues','lot_count','test_item_count'])}</div></details>
<h2>🚨 Immediate Action List</h2><details class="table-details immediate-actions"><summary>📋 View Immediate Action List</summary><div class="table-scroll">{dataframe_html(action_view, priority_columns)}</div></details>
<h2>📈 Capability Drift</h2><div class="panel">{trend_plot}</div>
<h2>🔬 Cpk Failing Test Parameter Diagnostics</h2><p class="note">Each section compares previous-day measurements against characterized production limits. Lot box plots follow the 00:00–23:59 sequence; tester box plots expose equipment-to-equipment distribution differences.</p>
{''.join(diagnostics)}
<h2>📐 Monthly Characterized-Limit Review</h2><p class="note">IQR filtering reduces one-time excursions using IQR = Q3 − Q1 and fences Q1 − 1.5×IQR to Q3 + 1.5×IQR.</p>
<details class="table-details"><summary>📋 View Monthly Characterized-Limit Review</summary><div class="table-scroll">{dataframe_html(rec_view, ['month','test_item','family','raw_count','IQR_removed_outliers','filtered_mean','filtered_stdev','current_lsl','current_usl','proposed_3s_lsl','proposed_3s_usl','proposed_6s_lsl','proposed_6s_usl','remarks'])}</div></details>
<p class="footer">Generated from deterministic synthetic data. No company, customer, product, or proprietary test information is included. Interactive plots require access to the Plotly CDN.</p>
</main></body></html>"""
    output_path.write_text(document, encoding="utf-8")


# ## 7. Run the complete pipeline
# 
# Change `OUTPUT_DIR` if needed, then run this cell. It writes every dataset and the HTML dashboard.
# 

# In[ ]:


OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

specs = build_specifications()
raw = generate_measurements(specs)
raw["event_time"] = pd.to_datetime(raw["event_time"])
raw["extraction_date"] = raw["event_time"].dt.normalize() + pd.Timedelta(days=1)
valid = raw[(raw["validation_status"] == "VALID") & raw["value"].notna()].copy()

lot_summary = build_lot_summary(valid)
period_summary = build_period_summary(valid)
recommendations = build_monthly_recommendations(valid)
extraction_manifest = (
    raw.groupby("extraction_date")
    .agg(
        source_records=("record_id", "size"),
        valid_records=("validation_status", lambda x: int((x == "VALID").sum())),
        validation_issues=("validation_status", lambda x: int((x != "VALID").sum())),
        lot_count=("lot_id", "nunique"),
        test_item_count=("test_item", "nunique"),
    )
    .reset_index()
    .sort_values("extraction_date")
)

specs.to_csv(OUTPUT_DIR / "synthetic_test_specifications.csv", index=False)
raw.to_csv(OUTPUT_DIR / "synthetic_test_measurements.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
lot_summary.to_csv(OUTPUT_DIR / "lot_parameter_capability.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
period_summary.to_csv(OUTPUT_DIR / "period_capability_summary.csv", index=False)
recommendations.to_csv(OUTPUT_DIR / "monthly_limit_recommendations.csv", index=False)
extraction_manifest.to_csv(OUTPUT_DIR / "daily_extraction_manifest.csv", index=False, date_format="%Y-%m-%d")
write_cleaned_records_log(raw, OUTPUT_DIR / "cleaned_data_records.xlsx")
build_html_report(raw, valid, lot_summary, period_summary, recommendations, extraction_manifest, OUTPUT_DIR / "semiconductor_test_capability_dashboard.html")

previous_day = valid["event_time"].dt.date.max()
previous_day_valid = valid[valid["event_time"].dt.date == previous_day]
previous_day_summary = (
    previous_day_valid.groupby(["test_item", "family"], sort=False)
    .apply(summarize_group, include_groups=False)
    .reset_index()
)
previous_day_summary["capability_status"] = previous_day_summary["cpk"].map(capability_status)

run_summary = {
    "raw_records": len(raw),
    "valid_records": len(valid),
    "test_items": specs["test_item"].nunique(),
    "previous_day": str(previous_day),
    "previous_day_lots": previous_day_valid["lot_id"].nunique(),
    "previous_day_failures": int((previous_day_summary["capability_status"] == "FAIL").sum()),
    "previous_day_warnings": int((previous_day_summary["capability_status"] == "WARNING").sum()),
    "report": str(OUTPUT_DIR / "semiconductor_test_capability_dashboard.html"),
}
run_summary


# ## 8. Inspect generated outputs
# 
# Use these views to confirm the daily extraction volumes and the highest-priority previous-day failures before opening the HTML dashboard.
# 

# In[ ]:


display(extraction_manifest.tail(10))

previous_day_summary.sort_values("cpk").loc[:, [
    "test_item", "family", "cpk", "cpu", "cpl", "mean", "stdev",
    "lsl", "usl", "capability_status"
]].head(20)


# ## 9. Open the dashboard
# 
# The interactive report is written to `output/semiconductor_test_capability_dashboard.html`. Open that file in Chrome or Edge. Plotly is loaded from a CDN, so interactive rendering requires network access.
# 
