"""
Module 5: Report Generator
Generates Excel reports and matplotlib charts for all workstreams.
"""
import os
import duckdb
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from rich.console import Console
from config import DB_PATH, OUTPUT_DIR, REPORTS_DIR, CHARTS_DIR

console = Console()


def generate_all_reports(validation_results, funnel_results):
    """Generate all output reports and charts."""
    console.print("\n[bold magenta]═══ GENERATING REPORTS & VISUALIZATIONS ═══[/]\n")

    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(CHARTS_DIR, exist_ok=True)

    generate_excel_report(validation_results, funnel_results)
    generate_funnel_chart(funnel_results["funnel"])
    generate_event_distribution_chart()
    generate_cohort_trend_chart(funnel_results["cohorts"])
    generate_data_quality_chart(validation_results)

    console.print(f"\n[bold green]✓ All reports saved to:[/] {OUTPUT_DIR}\n")


def generate_excel_report(validation_results, funnel_results):
    """Generate comprehensive Excel workbook."""
    filepath = os.path.join(REPORTS_DIR, "instrumentation_strategy_report.xlsx")
    console.print(f"  [cyan]→[/] Generating Excel report...")

    con = duckdb.connect(DB_PATH, read_only=True)

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        # --- Sheet 1: Executive Summary ---
        summary_data = []
        raw_count = con.execute("SELECT COUNT(*) FROM raw.dedicated_events").fetchone()[0]
        bi_count = con.execute("SELECT COUNT(*) FROM analytics.fct_dedicated_events").fetchone()[0]
        tenant_count = con.execute("SELECT COUNT(DISTINCT tenant_id) FROM analytics.dim_tenants").fetchone()[0]
        user_count = con.execute("SELECT COUNT(DISTINCT user_id) FROM analytics.dim_users").fetchone()[0]
        event_types = con.execute("SELECT COUNT(DISTINCT event_name) FROM raw.dedicated_events").fetchone()[0]

        summary_data = [
            {"Metric": "Total Raw Events", "Value": raw_count},
            {"Metric": "Total BI Events (Deduplicated)", "Value": bi_count},
            {"Metric": "Duplicate Events Removed", "Value": raw_count - bi_count},
            {"Metric": "Active Tenants", "Value": tenant_count},
            {"Metric": "Total Users", "Value": user_count},
            {"Metric": "Distinct Event Types", "Value": event_types},
            {"Metric": "Dedup Rate", "Value": f"{(raw_count - bi_count) / raw_count * 100:.2f}%"},
        ]
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Executive Summary", index=False)

        # --- Sheet 2: Event Volume by Category ---
        event_vol = con.execute("""
            SELECT
                event_category,
                event_name,
                COUNT(*) AS event_count,
                COUNT(DISTINCT tenant_id) AS tenants,
                COUNT(DISTINCT user_id) AS users,
                MIN(event_date) AS first_seen,
                MAX(event_date) AS last_seen
            FROM analytics.fct_dedicated_events
            GROUP BY event_category, event_name
            ORDER BY event_count DESC
        """).fetchdf()
        event_vol.to_excel(writer, sheet_name="Event Taxonomy Volume", index=False)

        # --- Sheet 3: Reconciliation Results ---
        if "reconciliation" in validation_results and validation_results["reconciliation"] is not None:
            recon = validation_results["reconciliation"]
            recon_summary = recon.groupby("status").agg(
                count=("event_name", "count"),
            ).reset_index()
            recon_summary.to_excel(writer, sheet_name="Reconciliation Summary", index=False)

        # --- Sheet 4: Data Quality — Null Checks ---
        if "null_checks" in validation_results and validation_results["null_checks"] is not None:
            validation_results["null_checks"].to_excel(writer, sheet_name="Null Field Checks", index=False)

        # --- Sheet 5: Duplicate Detection ---
        if "duplicates" in validation_results and validation_results["duplicates"] is not None:
            validation_results["duplicates"].to_excel(writer, sheet_name="Duplicate Events", index=False)

        # --- Sheet 6: Onboarding Funnel ---
        if "funnel" in funnel_results and funnel_results["funnel"] is not None:
            funnel_results["funnel"].to_excel(writer, sheet_name="Onboarding Funnel", index=False)

        # --- Sheet 7: Time-to-Complete ---
        if "time_to_complete" in funnel_results and funnel_results["time_to_complete"] is not None:
            funnel_results["time_to_complete"].to_excel(writer, sheet_name="Time to Complete", index=False)

        # --- Sheet 8: Role Segmentation ---
        if "segments" in funnel_results and funnel_results["segments"] is not None:
            funnel_results["segments"].to_excel(writer, sheet_name="Role Segmentation", index=False)

        # --- Sheet 9: Cohort Analysis ---
        if "cohorts" in funnel_results and funnel_results["cohorts"] is not None:
            funnel_results["cohorts"].to_excel(writer, sheet_name="Cohort Analysis", index=False)

        # --- Sheet 10: Tenant Overview ---
        tenants = con.execute("""
            SELECT
                t.tenant_id,
                t.tenant_name,
                t.region,
                t.plan_tier,
                t.seat_limit,
                t.sso_enabled,
                t.provisioning_date,
                COUNT(DISTINCT e.event_id) AS total_events,
                COUNT(DISTINCT e.user_id) AS active_users,
                COUNT(DISTINCT e.event_name) AS event_types_used
            FROM analytics.dim_tenants t
            LEFT JOIN analytics.fct_dedicated_events e ON e.tenant_id = t.tenant_id
            WHERE t.is_current = TRUE
            GROUP BY t.tenant_id, t.tenant_name, t.region, t.plan_tier,
                     t.seat_limit, t.sso_enabled, t.provisioning_date
            ORDER BY total_events DESC
        """).fetchdf()
        tenants.to_excel(writer, sheet_name="Tenant Overview", index=False)

        # --- Sheet 11: Data Model Schema ---
        schema_info = con.execute("""
            SELECT table_schema, table_name, column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema IN ('raw', 'analytics')
            ORDER BY table_schema, table_name, ordinal_position
        """).fetchdf()
        schema_info.to_excel(writer, sheet_name="Schema Reference", index=False)

    con.close()
    console.print(f"  [green]✓[/] Excel report: {filepath}")


def generate_funnel_chart(funnel_df):
    """Generate a funnel visualization chart."""
    filepath = os.path.join(CHARTS_DIR, "onboarding_funnel.png")

    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')

    steps = funnel_df["step_name"].tolist()
    users = funnel_df["users"].tolist()
    max_users = max(users) if users else 1

    colors = ['#58a6ff', '#56d4dd', '#3fb950', '#d2a8ff',
              '#f0883e', '#ff7b72', '#79c0ff', '#d29922']

    bars = ax.barh(range(len(steps) - 1, -1, -1), users, color=colors[:len(steps)],
                   edgecolor='#30363d', linewidth=0.5, height=0.6)

    for i, (bar, user_count) in enumerate(zip(bars, users)):
        pct = user_count / max_users * 100
        ax.text(bar.get_width() + max_users * 0.02, bar.get_y() + bar.get_height() / 2,
                f'{user_count:,} ({pct:.0f}%)', va='center', fontsize=10,
                color='#c9d1d9', fontweight='bold')

    ax.set_yticks(range(len(steps) - 1, -1, -1))
    ax.set_yticklabels(steps, fontsize=11, color='#c9d1d9')
    ax.set_xlabel('Users', fontsize=12, color='#8b949e')
    ax.set_title('GitLab Dedicated — Onboarding Funnel', fontsize=16,
                 color='#f0f6fc', fontweight='bold', pad=20)
    ax.set_xlim(0, max_users * 1.25)
    ax.tick_params(colors='#8b949e')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#30363d')
    ax.spines['left'].set_color('#30363d')
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{int(x):,}'))

    plt.tight_layout()
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    console.print(f"  [green]✓[/] Funnel chart: {filepath}")


def generate_event_distribution_chart():
    """Generate event distribution by category."""
    filepath = os.path.join(CHARTS_DIR, "event_distribution.png")
    con = duckdb.connect(DB_PATH, read_only=True)

    df = con.execute("""
        SELECT event_category, COUNT(*) AS count
        FROM analytics.fct_dedicated_events
        GROUP BY event_category
        ORDER BY count DESC
    """).fetchdf()
    con.close()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    fig.patch.set_facecolor('#0d1117')

    colors = ['#58a6ff', '#3fb950', '#d2a8ff', '#f0883e', '#ff7b72', '#56d4dd']

    # Pie chart
    ax1.set_facecolor('#0d1117')
    wedges, texts, autotexts = ax1.pie(
        df["count"], labels=df["event_category"], autopct='%1.1f%%',
        colors=colors[:len(df)], textprops={'color': '#c9d1d9', 'fontsize': 10},
        wedgeprops={'edgecolor': '#0d1117', 'linewidth': 2}
    )
    for autotext in autotexts:
        autotext.set_fontweight('bold')
    ax1.set_title('Event Distribution by Category', fontsize=14,
                  color='#f0f6fc', fontweight='bold')

    # Bar chart
    ax2.set_facecolor('#0d1117')
    bars = ax2.bar(df["event_category"], df["count"], color=colors[:len(df)],
                   edgecolor='#30363d', linewidth=0.5)
    for bar in bars:
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(df["count"]) * 0.02,
                 f'{int(bar.get_height()):,}', ha='center', va='bottom',
                 fontsize=9, color='#c9d1d9', fontweight='bold')
    ax2.set_ylabel('Event Count', fontsize=11, color='#8b949e')
    ax2.set_title('Event Volume by Category', fontsize=14,
                  color='#f0f6fc', fontweight='bold')
    ax2.tick_params(colors='#8b949e')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['bottom'].set_color('#30363d')
    ax2.spines['left'].set_color('#30363d')
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=25, ha='right')

    plt.tight_layout()
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    console.print(f"  [green]✓[/] Event distribution chart: {filepath}")


def generate_cohort_trend_chart(cohort_df):
    """Generate cohort trend line chart."""
    filepath = os.path.join(CHARTS_DIR, "cohort_trends.png")

    if cohort_df is None or len(cohort_df) == 0:
        return

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')

    x_labels = [str(w)[:10] for w in cohort_df["cohort_week"]]
    x_pos = range(len(x_labels))

    ax.plot(x_pos, cohort_df["accept_rate"], 'o-', color='#58a6ff',
            linewidth=2, markersize=8, label='Accept Rate %')
    ax.plot(x_pos, cohort_df["activation_rate"], 's-', color='#3fb950',
            linewidth=2, markersize=8, label='Activation Rate %')

    ax.set_xticks(list(x_pos))
    ax.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=9, color='#8b949e')
    ax.set_ylabel('Rate (%)', fontsize=12, color='#8b949e')
    ax.set_title('Onboarding Cohort Trends — Weekly', fontsize=16,
                 color='#f0f6fc', fontweight='bold', pad=15)
    ax.legend(loc='best', fontsize=10, facecolor='#161b22',
              edgecolor='#30363d', labelcolor='#c9d1d9')
    ax.tick_params(colors='#8b949e')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#30363d')
    ax.spines['left'].set_color('#30363d')
    ax.grid(True, alpha=0.15, color='#8b949e')

    plt.tight_layout()
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    console.print(f"  [green]✓[/] Cohort trend chart: {filepath}")


def generate_data_quality_chart(validation_results):
    """Generate data quality summary chart."""
    filepath = os.path.join(CHARTS_DIR, "data_quality_scorecard.png")

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.patch.set_facecolor('#0d1117')
    fig.suptitle('Data Quality Scorecard', fontsize=18, color='#f0f6fc',
                 fontweight='bold', y=1.02)

    # 1. Reconciliation Status
    ax = axes[0]
    ax.set_facecolor('#0d1117')
    if "reconciliation" in validation_results and validation_results["reconciliation"] is not None:
        recon = validation_results["reconciliation"]
        status_counts = recon["status"].value_counts()
        colors_map = {'🟢 PASS': '#3fb950', '🟡 WARN': '#d29922', '🔴 FAIL': '#f85149',
                      '🔴 ORPHAN': '#da3633', '🔴 MISSING': '#da3633'}
        vals = status_counts.values
        labels = [s.split(' ')[-1] for s in status_counts.index]
        bar_colors = [colors_map.get(s, '#8b949e') for s in status_counts.index]
        ax.bar(labels, vals, color=bar_colors, edgecolor='#30363d')
        for i, v in enumerate(vals):
            ax.text(i, v + max(vals) * 0.03, str(v), ha='center', color='#c9d1d9',
                    fontweight='bold', fontsize=11)
    ax.set_title('Reconciliation Status', fontsize=13, color='#c9d1d9', fontweight='bold')
    ax.tick_params(colors='#8b949e')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#30363d')
    ax.spines['left'].set_color('#30363d')

    # 2. Null Check Results
    ax = axes[1]
    ax.set_facecolor('#0d1117')
    if "null_checks" in validation_results and validation_results["null_checks"] is not None:
        nc = validation_results["null_checks"]
        total_nulls = int(nc["null_event_id"].sum() + nc["null_user_id"].sum() + nc["null_version"].sum())
        total_checks = int(nc["total_events"].sum() * 5)
        clean = total_checks - total_nulls
        ax.pie([clean, total_nulls], labels=['Clean', 'Null/Empty'],
               colors=['#3fb950', '#f85149'], autopct='%1.1f%%',
               textprops={'color': '#c9d1d9', 'fontsize': 11},
               wedgeprops={'edgecolor': '#0d1117', 'linewidth': 2})
    ax.set_title('Field Completeness', fontsize=13, color='#c9d1d9', fontweight='bold')

    # 3. Duplicate Rate
    ax = axes[2]
    ax.set_facecolor('#0d1117')
    con = duckdb.connect(DB_PATH, read_only=True)
    raw_total = con.execute("SELECT COUNT(*) FROM raw.dedicated_events").fetchone()[0]
    bi_total = con.execute("SELECT COUNT(*) FROM analytics.fct_dedicated_events").fetchone()[0]
    con.close()
    dup_count = raw_total - bi_total
    ax.pie([bi_total, dup_count], labels=['Unique', 'Duplicates'],
           colors=['#58a6ff', '#f0883e'], autopct='%1.1f%%',
           textprops={'color': '#c9d1d9', 'fontsize': 11},
           wedgeprops={'edgecolor': '#0d1117', 'linewidth': 2})
    ax.set_title('Event Deduplication', fontsize=13, color='#c9d1d9', fontweight='bold')

    plt.tight_layout()
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    console.print(f"  [green]✓[/] Data quality scorecard: {filepath}")
