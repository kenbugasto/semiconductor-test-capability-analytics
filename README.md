# 📊 Semiconductor Test Capability & SPC Analytics

Synthetic semiconductor test analytics pipeline built with **Python, Pandas, NumPy, XlsxWriter, and Plotly**. Automates test-data validation, statistical capability analysis, and interactive HTML reporting for lot, tester, and test-site investigations.

> **Data disclaimer:** All datasets, lot identifiers, tester names, site IDs, and specification limits are synthetic. No proprietary manufacturing or customer-sensitive information is included.

## 🔎 Problem and Engineering Value

Semiconductor test capability investigations involve reviewing measurement distributions across production lots, testers, and test sites. Manual analysis makes it difficult to identify parameter drift, tester-related shifts, and process variation.

This project automates capability screening and diagnostic reporting to help engineers identify problematic parameters, investigate potential causes, and prioritize engineering actions.

## 🖥️ Interactive Demo

| Dashboard | Purpose | Demo |
| --- | --- | --- |
| Test Capability Report | Cpk screening, lot/tester/site distributions, parameter trends, and engineering action priorities | [Open dashboard](demo/semiconductor_test_capability_dashboard.html) |

> **GitHub Pages:** After publishing the `demo/` folder through GitHub Pages, replace the relative link above with the verified public dashboard URL.

## 🔄 Pipeline Workflow

1. Generate 30 days of synthetic test data covering **100 parameters, 118 lots, 4 testers, and 8 test sites per tester**.
2. Validate records and separate missing values, duplicates, and invalid tester entries.
3. Calculate lot-level and periodic statistics, including mean, standard deviation, Cpu, Cpl, and Cpk.
4. Screen for capability failures and investigate parameter drift, tester shifts, increased variation, and sudden excursions.
5. Generate diagnostic distributions, engineering action lists, and monthly specification-limit review candidates.
6. Export interactive HTML dashboards, CSV datasets, and Excel validation records.

## 📐 Capability Definitions

**Cpk = min(Cpu, Cpl)**

- **Cpu:** (USL − Mean) / (3 × Standard Deviation)
- **Cpl:** (Mean − LSL) / (3 × Standard Deviation)
- **USL / LSL:** Upper and lower specification limits.

| Cpk | Classification |
| --- | --- |
| Cpk < 1.33 | FAIL |
| 1.33 ≤ Cpk < 1.67 | WARNING |
| 1.67 ≤ Cpk < 2.00 | 5σ Parameters |
| Cpk ≥ 2.00 | 6σ Parameters |

These are **project-defined screening categories**, not universal manufacturing acceptance criteria.

## ⚠️ SPC Scope and Limitations

This project focuses on **process capability analysis and trend monitoring**, rather than a complete classical Statistical Process Control (SPC) implementation.

It evaluates measurement distributions, Cpk performance, parameter drift, and tester/site variation. It **does not implement statistical control charts** such as X-bar/R or I-MR, or automated Nelson/Western Electric control rules.

Capability results support engineering investigation and do not automatically determine production lot disposition. Formal production capability assessment would also require appropriate process-stability, distribution, and measurement-system checks.

## 🛠️ Engineering Decisions

- **Synthetic production simulation:** Reproducible datasets with controlled drift, tester shifts, increased variation, and excursions.
- **Data-quality traceability:** Invalid and duplicate records are retained separately from valid measurements.
- **Production-style lot assignment:** Each synthetic sublot is assigned to one tester, with eight test sites represented.
- **Interactive diagnostics:** Plotly box plots compare lot, tester, and site distributions against specification limits.
- **Engineering limit review:** IQR-based filtering and sigma-range calculations generate proposed limits for review, not automatic implementation.
- **Standalone HTML reporting:** Interactive dashboards can be reviewed without a dedicated dashboard server.

## 💻 Technology Stack

**Python · Pandas · NumPy · Plotly · XlsxWriter · HTML · Statistical Capability Analysis**

## 🚀 Running the Project

See [HOW_TO_RUN.md](HOW_TO_RUN.md) for installation, execution, and generated outputs.
