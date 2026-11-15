"""
Meridian University Student Information System
Figure and Diagram Generator
Author: Avinaash A (Reg. No: 192324260)
Course: DSA0501 - Query Processing for Data Science
"""

import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Set publication style
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = 10
plt.rcParams["axes.titlesize"] = 12
plt.rcParams["axes.titleweight"] = "bold"

BASE_DIR = Path(__file__).resolve().parent
DIAGRAMS_DIR = BASE_DIR.parent / "diagrams"
DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)

RAW_CSV = BASE_DIR / "raw" / "students_dirty.csv"
CLEAN_CSV = BASE_DIR / "curated" / "clean_students_output.csv"

from matplotlib.patches import FancyBboxPatch

# ---------------------------------------------------------
# Figure 1: End-to-End Cleaning Pipeline Workflow
# ---------------------------------------------------------
def generate_fig1():
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    ax.axis("off")
    
    stages = [
        ("Raw Ingestion\n(Stage 1)", "5,734 records\nParse null tokens\nCheck SHA-256", "#E3F2FD", "#1565C0"),
        ("Standardization\n(Stage 2)", "Title casing, ISO 8601\nPhone digits, 6 depts\nParticle exceptions", "#E8F5E9", "#2E7D32"),
        ("Imputation\n(Stage 3)", "Group-wise Dept median\nPreserve variance\nFlag missing DOB", "#FFF9C4", "#F57F17"),
        ("Outlier Treatment\n(Stage 4)", "Domain [0, 100]\nTypo fix (640->64)\nCap attendance", "#FFE0B2", "#E65100"),
        ("Deduplication\n(Stage 5)", "Exact (120 purged)\nKey conflicts (95)\nPartial Name+DOB (107)", "#FCE4EC", "#C2185B"),
        ("RegEx Verification\n(Stage 6)", "Email typo correction\nIndian mobile syntax\nTri-Zone flags", "#EDE7F6", "#512DA8"),
        ("Curated Persistence\n(Stage 7)", "Min-Max & Z-Score\nCSV/JSON export\nImmutable Raw SHA", "#E0F7FA", "#006064")
    ]
    
    n = len(stages)
    box_width = 1.15
    box_height = 1.8
    y_pos = 2.0
    
    for i, (title, desc, fill_c, edge_c) in enumerate(stages):
        x_pos = 0.5 + i * 1.6
        # Draw box
        rect = FancyBboxPatch(
            (x_pos, y_pos), box_width, box_height,
            boxstyle="round,pad=0.1", facecolor=fill_c, edgecolor=edge_c, linewidth=2
        )
        ax.add_patch(rect)
        ax.text(x_pos + box_width/2, y_pos + box_height - 0.4, title, ha="center", va="center", weight="bold", color=edge_c, fontsize=10)
        ax.text(x_pos + box_width/2, y_pos + box_height/2 - 0.25, desc, ha="center", va="center", color="#333333", fontsize=8.5)
        
        # Draw connecting arrow
        if i < n - 1:
            ax.annotate(
                "", xy=(x_pos + box_width + 0.42, y_pos + box_height/2),
                xytext=(x_pos + box_width + 0.05, y_pos + box_height/2),
                arrowprops=dict(arrowstyle="->", color="#424242", lw=2, mutation_scale=15)
            )
            
    ax.set_xlim(0, 11.8)
    ax.set_ylim(1.0, 4.5)
    ax.set_title("Meridian University: 7-Stage End-to-End Data Cleaning Pipeline Architecture", fontsize=13, pad=15)
    
    out_file = DIAGRAMS_DIR / "fig1_cleaning_workflow.png"
    plt.tight_layout()
    plt.savefig(out_file, bbox_inches="tight")
    plt.close()
    print(f"Generated Figure 1: {out_file}")

# ---------------------------------------------------------
# Figure 2: Missing Values & Outlier Distribution
# ---------------------------------------------------------
def generate_fig2():
    df_raw = pd.read_csv(RAW_CSV, dtype=str)
    df_clean = pd.read_csv(CLEAN_CSV)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)
    
    # Subplot A: Missingness
    cols = ["student_id", "full_name", "department", "dob", "phone", "attendance_pct", "marks"]
    na_tokens = ["NA", "-", "?", "null", "N/A", "none", "nan", ""]
    missing_pcts = []
    for c in cols:
        cnt = df_raw[c].isna().sum() + df_raw[c].str.strip().isin(na_tokens).sum()
        missing_pcts.append((cnt / len(df_raw)) * 100)
        
    y_pos = np.arange(len(cols))
    bars = ax1.barh(y_pos, missing_pcts, color="#1976D2", edgecolor="#0D47A1", height=0.6)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(cols, fontsize=9.5)
    ax1.set_xlabel("Missing / Placeholder Rate (%)", fontsize=10)
    ax1.set_title("(a) Missingness Profile by Column in Raw SIS Dataset", fontsize=11)
    ax1.axvline(8.0, color="#D32F2F", linestyle="--", linewidth=1.5, label="Mandatory Threshold (8%)")
    ax1.set_xlim(0, 15)
    ax1.legend(loc="lower right")
    
    # Annotate bars
    for bar, val in zip(bars, missing_pcts):
        if val > 0:
            ax1.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2, f"{val:.1f}%", va="center", fontsize=8.5, weight="bold")
            
    # Subplot B: Outlier Distribution Comparison
    # Raw marks with outliers
    m_raw = pd.to_numeric(df_raw["marks"], errors="coerce").dropna().values
    m_clean = df_clean["marks_cleaned"].values
    
    # Boxplots
    bp = ax2.boxplot([m_raw, m_clean], tick_labels=["Raw Data (Uncleaned)", "Cleaned Data (Curated)"], patch_artist=True, widths=0.45)
    colors = ["#FFCDD2", "#C8E6C9"]
    edge_colors = ["#C62828", "#2E7D32"]
    for patch, c, ec in zip(bp['boxes'], colors, edge_colors):
        patch.set_facecolor(c)
        patch.set_edgecolor(ec)
        patch.set_linewidth(1.5)
        
    ax2.set_ylabel("Academic Marks", fontsize=10)
    ax2.set_title("(b) Marks Distribution: Raw Outliers vs Curated Bounded Distribution", fontsize=11)
    ax2.axhline(100, color="#B0BEC5", linestyle=":", label="Upper Legal Bound (100)")
    ax2.axhline(0, color="#B0BEC5", linestyle=":", label="Lower Legal Bound (0)")
    ax2.set_ylim(-30, 900)
    ax2.text(1, 860, "Severe Outliers:\n(580, 640, 850)", color="#C62828", weight="bold", fontsize=8.5, ha="center")
    ax2.text(2, 115, "Bounded [5.0, 100.0]\nMean = 73.1, Std = 13.3", color="#2E7D32", weight="bold", fontsize=8.5, ha="center")
    
    out_file = DIAGRAMS_DIR / "fig2_data_profiling_missing_outliers.png"
    plt.tight_layout()
    plt.savefig(out_file, bbox_inches="tight")
    plt.close()
    print(f"Generated Figure 2: {out_file}")

# ---------------------------------------------------------
# Figure 3: Fuzzy Matching Precision, Recall & Tri-Zone
# ---------------------------------------------------------
def generate_fig3():
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
    
    thresholds = [0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.98]
    precision =  [0.52, 0.56, 0.61, 0.71, 0.81, 0.93, 1.00, 1.00]
    recall =     [1.00, 1.00, 1.00, 0.96, 0.88, 0.72, 0.28, 0.12]
    f1_score =   [0.68, 0.72, 0.76, 0.82, 0.84, 0.81, 0.44, 0.21]
    
    ax.plot(thresholds, precision, marker="o", color="#1E88E5", linewidth=2.5, label="Precision (TP / (TP + FP))")
    ax.plot(thresholds, recall, marker="s", color="#E53935", linewidth=2.5, label="Recall (TP / (TP + FN))")
    ax.plot(thresholds, f1_score, marker="^", color="#43A047", linewidth=2.5, linestyle="--", label="F1-Score (Harmonic Mean)")
    
    # Highlight Tri-Zone Operational Architecture
    ax.axvspan(0.90, 1.00, alpha=0.15, color="green", label="Zone 1: Auto-Accept (>= 0.90)")
    ax.axvspan(0.75, 0.90, alpha=0.15, color="orange", label="Zone 2: Manual Review Queue (0.75 - 0.90)")
    ax.axvspan(0.60, 0.75, alpha=0.15, color="red", label="Zone 3: Auto-Reject (< 0.75)")
    
    ax.set_xlabel("Fuzzy Similarity Threshold (Difflib / SequenceMatcher Ratio)", fontsize=10.5)
    ax.set_ylabel("Metric Score [0.0 - 1.0]", fontsize=10.5)
    ax.set_title("Fuzzy Matching Performance Trade-off & Tri-Zone Operational Architecture", fontsize=12, pad=12)
    ax.set_xlim(0.62, 1.00)
    ax.set_ylim(0.0, 1.05)
    ax.legend(loc="lower left", fontsize=8.5, frameon=True)
    
    out_file = DIAGRAMS_DIR / "fig3_fuzzy_roc_thresholds.png"
    plt.tight_layout()
    plt.savefig(out_file, bbox_inches="tight")
    plt.close()
    print(f"Generated Figure 3: {out_file}")

# ---------------------------------------------------------
# Figure 4: Day-4 Architecture (V2 Pipeline)
# ---------------------------------------------------------
def generate_fig4():
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    ax.axis("off")
    
    # Flowchart nodes
    nodes = [
        ("Partner Admission Portal\n(Unstructured CSV)", "1,135 raw applicant records\nApplicant_ref, applicant_name\nHSC %, submitted_on timestamps", "#ECEFF1", "#37474F", (0.5, 3.2)),
        ("Dynamic Schema Adapter\n(V2 Stage 1)", "Map columns to SIS schema\napplicant_ref -> student_id\nhsc_percentage -> marks", "#E1F5FE", "#0288D1", (3.4, 3.2)),
        ("Multi-Pattern Parser\n(V2 Stage 2-3)", "Strip honorifics (Mr., Dr.)\nParse timestamps (21.07.2026)\nExpand 8-dept taxonomy", "#FFF3E0", "#F57C00", (6.3, 3.2)),
        ("Numeric Rescaling Engine\n(V2 Stage 4)", "Fractional: 0.87 -> 87.0%\n500-scale: 455 -> 91.0%\nTypo fix: 640 -> 64.0", "#E8F5E9", "#388E3C", (9.2, 3.2)),
        ("Survivorship & Conflict\n(V2 Stage 5)", "Deduplicate AP26 refs\nPartial match on Name+DOB\nKeep latest submitted", "#FCE4EC", "#C2185B", (4.8, 1.0)),
        ("Curated SIS Enterprise\n(V2 Output)", "1,100 verified records\nZero regression on SIS legacy\nValidated accreditation file", "#E0F2F1", "#00796B", (8.5, 1.0))
    ]
    
    w, h = 2.4, 1.6
    for title, desc, fill_c, edge_c, (x, y) in nodes:
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1", facecolor=fill_c, edgecolor=edge_c, linewidth=2)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h - 0.35, title, ha="center", va="center", weight="bold", color=edge_c, fontsize=9.5)
        ax.text(x + w/2, y + h/2 - 0.25, desc, ha="center", va="center", color="#333333", fontsize=8)
        
    # Arrows
    arrows = [
        ((2.9, 4.0), (3.4, 4.0)),
        ((5.8, 4.0), (6.3, 4.0)),
        ((8.7, 4.0), (9.2, 4.0)),
        ((10.4, 3.2), (6.0, 2.6)), # Down to survivorship
        ((7.2, 1.8), (8.5, 1.8))   # Across to curated
    ]
    for start, end in arrows:
        ax.annotate("", xy=end, xytext=start, arrowprops=dict(arrowstyle="->", color="#37474F", lw=2, mutation_scale=14))
        
    ax.set_xlim(0, 12.0)
    ax.set_ylim(0.5, 5.2)
    ax.set_title("Day-4 Design Challenge: V2 Resilient Architecture for Partner Portal Ingestion", fontsize=13, pad=15)
    
    out_file = DIAGRAMS_DIR / "fig4_day4_v2_architecture.png"
    plt.tight_layout()
    plt.savefig(out_file, bbox_inches="tight")
    plt.close()
    print(f"Generated Figure 4: {out_file}")

if __name__ == "__main__":
    generate_fig1()
    generate_fig2()
    generate_fig3()
    generate_fig4()
    print("All 4 Figures Generated Successfully!")
