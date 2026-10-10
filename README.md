# 📊 Semiconductor Test Capability & SPC Analytics

Synthetic semiconductor test analytics pipeline built with **Python, Pandas, NumPy, XlsxWriter, and Plotly**. Automates measurement validation, statistical capability analysis, and interactive HTML reporting for lot, tester, and test-site investigations.

> **Public portfolio:** All measurements, lots, testers, site identifiers, and specification limits are synthetic. No proprietary manufacturing or customer-sensitive information is included.

## 🔎 Problem and Engineering Value

Semiconductor test capability investigations involve comparing large volumes of measurement data across lots, testers, and sites. Manual analysis makes it difficult to identify parameter drift, tester-related shifts, and process variation.

This project automates capability screening and diagnostic reporting to help engineers prioritize parameters for investigation and review potential sources of variation.

## 🚀 Interactive Demo

| Dashboard | Purpose | Demo |
| --- | --- | --- |
| Test Capability Report | Cpk screening, parameter trends, lot/tester/site distributions, and engineering priorities | [Open](https://kenbugasto.github.io/semiconductor-test-capability-analytics/demo/semiconductor_test_capability_dashboard.html) |

HTML demos open directly in a browser without Python or a database connection, once GitHub Pages is published. Plotly charts require an internet connection.

## ⚙️ Workflow and How to Run

### Processing Workflow

1. Generate 30 days of synthetic test measurements covering **100 parameters, 118 sublots, 4 testers, and 8 sites per tester**.
2. Validate records and separate missing values, duplicates, and invalid tester entries.
3. Calculate lot-level and periodic statistics: mean, standard deviation, Cpu, Cpl, and Cpk.
4. Screen for capability failures, parameter drift, tester shifts, increased variation, and sudden excursions.
5. Prepare diagnostic plots and monthly specification-limit review candidates.
6. Export an interactive HTML dashboard, CSV datasets, and an Excel data-quality log.

## 📐 Capability Definitions

**Cpk = min(Cpu, Cpl)**

- **Cpu:** (USL − Mean) / (3 × Standard Deviation)
- **Cpl:** (Mean − LSL) / (3 × Standard Deviation)
- **USL / LSL:** Upper and lower specification limits

| Cpk | Project screening category |
| --- | --- |
| Below 1.33 | FAIL |
| 1.33 to below 1.67 | WARNING |
| 1.67 to below 2.00 | 5σ Parameters |
| 2.00 and above | 6σ Parameters |

These are **project-defined screening thresholds**, not universal manufacturing acceptance criteria.

## 📌 SPC Scope and Limitations

This project focuses on **process capability analysis and trend monitoring**, not a complete classical Statistical Process Control (SPC) implementation.

It analyzes measurement distributions, Cpk performance, parameter drift, and tester/site variation. It does **not** implement X-bar/R or I-MR control charts or automated Nelson/Western Electric control rules. Formal production capability assessments also require appropriate checks of process stability, distribution assumptions, and measurement-system suitability.

Results support engineering investigation; they do not automatically approve specification changes or determine lot disposition.

### Run Locally

**Requirements:** Python with compatible versions of Pandas, NumPy, XlsxWriter, and OpenPyXL. VS Code with the Python and Jupyter extensions is recommended for the notebook.

**1. Install dependencies** in your Python environment:

```bash
python -m pip install numpy pandas xlsxwriter openpyxl
```

Or, from a VS Code/Jupyter notebook cell, install into the active kernel:

```python
%pip install numpy pandas xlsxwriter openpyxl
```

**2. Run either version:**

- **Notebook:** Open `semiconductor_test_capability_analytics_tool.ipynb`, select the Python kernel, and choose **Run All**.
- **Python script:** Run `python semiconductor_test_capability_analytics_tool.py` from the project directory.

**3. Review the generated `output/` folder.** Key files include:

| Output | Purpose |
| --- | --- |
| `semiconductor_test_capability_dashboard.html` | Interactive capability and diagnostic report |
| `lot_parameter_capability.csv` | Lot-level capability calculations |
| `period_capability_summary.csv` | Periodic capability summaries |
| `monthly_limit_recommendations.csv` | Proposed limits for engineering review |
| `daily_extraction_manifest.csv` | Daily record-count tracking |
| `cleaned_data_records.xlsx` | Invalid/duplicate record log |

Open `output/semiconductor_test_capability_dashboard.html` in a web browser. The script generates synthetic data locally and does not require company systems, FTP access, or a production database.

## 🏭 Production Automation Reference

The synthetic portfolio is a **standalone demonstration**, inspired by a separate production VCL test-capability reporting workflow.

In the production workflow, the reporting tool runs **every three hours starting at 06:00**. At **06:00 the following day**, the prior day's runs are consolidated into a full-day report. This supports both intraday monitoring and a complete daily engineering review.

The production tool also packages large HTML reports into dated ZIP archives and applies short-term output retention. **These scheduling, consolidation, and retention operations are not implemented by the synthetic portfolio notebook.**

## 🛠️ Engineering Decisions

- **Synthetic fault injection:** Reproducible examples of drift, tester shifts, increased variation, and excursions.
- **Data-quality traceability:** Invalid records are logged separately rather than silently discarded.
- **Lot/tester consistency:** Each synthetic sublot is assigned to one tester with eight test sites.
- **Interactive diagnostics:** Plotly distributions support comparisons by lot, tester, and site against specification limits.
- **Limit-review safeguards:** IQR-based filtering generates candidates for engineering evaluation, never automatic limit changes.
- **Portable reporting:** HTML output does not require a dashboard server.

## 🧰 Technology Stack

**Python · Pandas · NumPy · Plotly · XlsxWriter · OpenPyXL · HTML · Statistical Capability Analysis**
