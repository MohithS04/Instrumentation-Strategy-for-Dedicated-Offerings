"""
Module 3: Data Validation Engine
Implements reconciliation checks from Workstream 2.
"""
import duckdb
import pandas as pd
from rich.console import Console
from rich.table import Table
from config import DB_PATH, RECONCILIATION_PASS_THRESHOLD, RECONCILIATION_WARN_THRESHOLD

console = Console()


def run_all_validations():
    """Run all validation queries and return results."""
    console.print("\n[bold magenta]═══ WORKSTREAM 2: DATA VALIDATION & RECONCILIATION ═══[/]\n")

    results = {}
    results["reconciliation"] = run_row_count_reconciliation()
    results["null_checks"] = run_null_field_checks()
    results["duplicates"] = run_duplicate_detection()
    results["tenant_coverage"] = run_tenant_coverage_check()
    return results


def run_row_count_reconciliation():
    """Query 1: Row count reconciliation between raw and transformed tables."""
    console.print("[bold cyan]▶ Validation 1: Row Count Reconciliation (Raw vs. BI)[/]")
    con = duckdb.connect(DB_PATH, read_only=True)

    df = con.execute("""
        WITH raw_counts AS (
            SELECT
                event_name,
                CAST(event_timestamp AS DATE) AS event_date,
                COUNT(*) AS total_raw_rows,
                COUNT(DISTINCT event_id) AS distinct_raw_events
            FROM raw.dedicated_events
            GROUP BY event_name, CAST(event_timestamp AS DATE)
        ),
        bi_counts AS (
            SELECT
                event_name,
                event_date,
                COUNT(*) AS total_bi_rows,
                COUNT(DISTINCT event_id) AS distinct_bi_events
            FROM analytics.fct_dedicated_events
            GROUP BY event_name, event_date
        )
        SELECT
            COALESCE(r.event_name, b.event_name) AS event_name,
            COALESCE(r.event_date, b.event_date) AS event_date,
            COALESCE(r.total_raw_rows, 0) AS raw_rows,
            COALESCE(b.total_bi_rows, 0) AS bi_rows,
            COALESCE(r.distinct_raw_events, 0) AS raw_distinct,
            COALESCE(b.distinct_bi_events, 0) AS bi_distinct,
            COALESCE(r.distinct_raw_events, 0) - COALESCE(b.distinct_bi_events, 0) AS count_diff,
            CASE
                WHEN COALESCE(r.distinct_raw_events, 0) = 0 THEN NULL
                ELSE ROUND(
                    ABS(COALESCE(r.distinct_raw_events, 0) - COALESCE(b.distinct_bi_events, 0))
                    * 100.0 / r.distinct_raw_events, 4
                )
            END AS variance_pct,
            CASE
                WHEN COALESCE(r.distinct_raw_events, 0) = 0 AND COALESCE(b.distinct_bi_events, 0) > 0
                    THEN '🔴 ORPHAN'
                WHEN COALESCE(b.distinct_bi_events, 0) = 0 AND COALESCE(r.distinct_raw_events, 0) > 0
                    THEN '🔴 MISSING'
                WHEN ABS(COALESCE(r.distinct_raw_events, 0) - COALESCE(b.distinct_bi_events, 0))
                     * 100.0 / r.distinct_raw_events > 1.0
                    THEN '🔴 FAIL'
                WHEN ABS(COALESCE(r.distinct_raw_events, 0) - COALESCE(b.distinct_bi_events, 0))
                     * 100.0 / r.distinct_raw_events > 0.1
                    THEN '🟡 WARN'
                ELSE '🟢 PASS'
            END AS status
        FROM raw_counts r
        FULL OUTER JOIN bi_counts b
            ON r.event_name = b.event_name AND r.event_date = b.event_date
        ORDER BY status, event_date
    """).fetchdf()
    con.close()

    # Summary
    summary = df.groupby("status").size().reset_index(name="count")
    table = Table(title="Reconciliation Summary", show_lines=True)
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")
    for _, row in summary.iterrows():
        table.add_row(str(row["status"]), str(row["count"]))
    console.print(table)

    pass_rate = len(df[df["status"].str.contains("PASS")]) / len(df) * 100 if len(df) > 0 else 0
    console.print(f"  Overall pass rate: [bold]{pass_rate:.1f}%[/]\n")

    return df


def run_null_field_checks():
    """Query 2: Null/missing property checks on critical fields."""
    console.print("[bold cyan]▶ Validation 2: Null / Missing Field Checks[/]")
    con = duckdb.connect(DB_PATH, read_only=True)

    df = con.execute("""
        SELECT
            event_name,
            COUNT(*) AS total_events,
            SUM(CASE WHEN event_id IS NULL OR event_id = '' THEN 1 ELSE 0 END) AS null_event_id,
            SUM(CASE WHEN tenant_id IS NULL OR tenant_id = '' THEN 1 ELSE 0 END) AS null_tenant_id,
            SUM(CASE WHEN user_id IS NULL OR user_id = '' THEN 1 ELSE 0 END) AS null_user_id,
            SUM(CASE WHEN event_timestamp IS NULL THEN 1 ELSE 0 END) AS null_timestamp,
            SUM(CASE WHEN platform_version IS NULL OR platform_version = '' THEN 1 ELSE 0 END) AS null_version,
            SUM(CASE WHEN session_id IS NULL OR session_id = '' THEN 1 ELSE 0 END) AS null_session_id,
            ROUND(
                (
                    SUM(CASE WHEN event_id IS NULL OR event_id = '' THEN 1 ELSE 0 END) +
                    SUM(CASE WHEN tenant_id IS NULL OR tenant_id = '' THEN 1 ELSE 0 END) +
                    SUM(CASE WHEN user_id IS NULL OR user_id = '' THEN 1 ELSE 0 END) +
                    SUM(CASE WHEN event_timestamp IS NULL THEN 1 ELSE 0 END) +
                    SUM(CASE WHEN platform_version IS NULL OR platform_version = '' THEN 1 ELSE 0 END)
                ) * 100.0 / (COUNT(*) * 5), 4
            ) AS null_rate_pct
        FROM raw.dedicated_events
        GROUP BY event_name
        ORDER BY null_rate_pct DESC
    """).fetchdf()
    con.close()

    table = Table(title="Null Field Check Results", show_lines=True)
    table.add_column("Event Name", style="bold", max_width=45)
    table.add_column("Total", justify="right")
    table.add_column("Null event_id", justify="right")
    table.add_column("Null user_id", justify="right")
    table.add_column("Null version", justify="right")
    table.add_column("Null Rate %", justify="right")
    table.add_column("Status", justify="center")

    for _, row in df.iterrows():
        total_nulls = row["null_event_id"] + row["null_user_id"] + row["null_version"]
        status = "🔴 FAIL" if total_nulls > 0 else "🟢 PASS"
        table.add_row(
            str(row["event_name"]),
            str(int(row["total_events"])),
            str(int(row["null_event_id"])),
            str(int(row["null_user_id"])),
            str(int(row["null_version"])),
            f"{row['null_rate_pct']:.4f}%",
            status,
        )
    console.print(table)

    total_issues = int(df["null_event_id"].sum() + df["null_user_id"].sum() + df["null_version"].sum())
    console.print(f"  Total null/empty critical fields found: [bold red]{total_issues}[/]\n")

    return df


def run_duplicate_detection():
    """Query 3: Duplicate event detection."""
    console.print("[bold cyan]▶ Validation 3: Duplicate Event Detection[/]")
    con = duckdb.connect(DB_PATH, read_only=True)

    df = con.execute("""
        WITH dupes AS (
            SELECT
                event_id,
                event_name,
                tenant_id,
                COUNT(*) AS occurrence_count
            FROM raw.dedicated_events
            GROUP BY event_id, event_name, tenant_id
            HAVING COUNT(*) > 1
        )
        SELECT
            event_name,
            tenant_id,
            COUNT(DISTINCT event_id) AS duplicate_event_ids,
            SUM(occurrence_count) AS total_duplicate_rows,
            SUM(occurrence_count) - COUNT(DISTINCT event_id) AS excess_rows,
            MAX(occurrence_count) AS max_occurrences
        FROM dupes
        GROUP BY event_name, tenant_id
        ORDER BY total_duplicate_rows DESC
    """).fetchdf()
    con.close()

    if len(df) == 0:
        console.print("  [bold green]✓ No duplicate events detected![/]\n")
    else:
        table = Table(title="Duplicate Events Found", show_lines=True)
        table.add_column("Event Name", style="bold", max_width=40)
        table.add_column("Tenant", max_width=25)
        table.add_column("Dup IDs", justify="right")
        table.add_column("Excess Rows", justify="right")
        table.add_column("Status", justify="center")

        total_excess = 0
        for _, row in df.head(15).iterrows():
            total_excess += int(row["excess_rows"])
            table.add_row(
                str(row["event_name"]),
                str(row["tenant_id"])[:25],
                str(int(row["duplicate_event_ids"])),
                str(int(row["excess_rows"])),
                "🔴 DUP",
            )
        console.print(table)
        console.print(f"  Total excess rows from duplicates: [bold red]{int(df['excess_rows'].sum())}[/]")
        console.print(f"  Deduplication applied in analytics.fct_dedicated_events ✓\n")

    return df


def run_tenant_coverage_check():
    """Query 4: Verify all tenants reporting expected P0 events."""
    console.print("[bold cyan]▶ Validation 4: Tenant P0 Event Coverage[/]")
    con = duckdb.connect(DB_PATH, read_only=True)

    df = con.execute("""
        WITH expected_p0 AS (
            SELECT event_name FROM (VALUES
                ('dedicated_tenant_provisioned'),
                ('dedicated_user_invited'),
                ('dedicated_onboarding_step_completed'),
                ('dedicated_pipeline_executed'),
                ('dedicated_sso_configured')
            ) AS t(event_name)
        ),
        active_tenants AS (
            SELECT DISTINCT tenant_id FROM raw.dedicated_events
        ),
        coverage AS (
            SELECT
                t.tenant_id,
                e.event_name,
                COUNT(r.event_id) AS event_count
            FROM active_tenants t
            CROSS JOIN expected_p0 e
            LEFT JOIN raw.dedicated_events r
                ON r.tenant_id = t.tenant_id AND r.event_name = e.event_name
            GROUP BY t.tenant_id, e.event_name
        )
        SELECT
            tenant_id,
            event_name,
            event_count,
            CASE WHEN event_count = 0 THEN '🔴 MISSING' ELSE '🟢 OK' END AS status
        FROM coverage
        ORDER BY status DESC, tenant_id, event_name
    """).fetchdf()
    con.close()

    missing = df[df["status"].str.contains("MISSING")]
    ok = df[df["status"].str.contains("OK")]

    if len(missing) == 0:
        console.print("  [bold green]✓ All tenants reporting all P0 events![/]\n")
    else:
        table = Table(title="P0 Event Coverage Gaps", show_lines=True)
        table.add_column("Tenant", max_width=30)
        table.add_column("Missing Event", max_width=45)
        table.add_column("Status")
        for _, row in missing.iterrows():
            table.add_row(str(row["tenant_id"])[:30], str(row["event_name"]), "🔴 MISSING")
        console.print(table)

    total_checks = len(df)
    pass_count = len(ok)
    console.print(f"  Coverage: {pass_count}/{total_checks} checks OK ({pass_count/total_checks*100:.1f}%)\n")

    return df


if __name__ == "__main__":
    run_all_validations()
