"""
Module 4: Onboarding Funnel Analysis Engine
Implements Workstream 3 — quantitative onboarding friction analysis.
"""
import duckdb
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from config import DB_PATH, FUNNEL_STEPS, FUNNEL_BENCHMARKS

console = Console()


def run_funnel_analysis():
    """Execute the full onboarding funnel analysis."""
    console.print("\n[bold magenta]═══ WORKSTREAM 3: ONBOARDING FUNNEL ANALYSIS ═══[/]\n")

    funnel_df = compute_funnel()
    time_df = compute_time_to_complete()
    segment_df = compute_segment_analysis()
    cohort_df = compute_cohort_analysis()

    return {
        "funnel": funnel_df,
        "time_to_complete": time_df,
        "segments": segment_df,
        "cohorts": cohort_df,
    }


def compute_funnel():
    """Compute the 8-step onboarding funnel."""
    console.print("[bold cyan]▶ Onboarding Funnel — Step-by-Step Conversion[/]")
    con = duckdb.connect(DB_PATH, read_only=True)

    df = con.execute("""
        WITH invited AS (
            SELECT DISTINCT user_id, tenant_id, MIN(event_timestamp) AS invited_at
            FROM raw.dedicated_events
            WHERE event_name = 'dedicated_user_invited'
            GROUP BY user_id, tenant_id
        ),
        step_completions AS (
            SELECT
                i.user_id,
                i.tenant_id,
                i.invited_at,
                MIN(CASE WHEN e.event_name = 'dedicated_user_invitation_accepted'
                         THEN e.event_timestamp END) AS step_1_at,
                MIN(CASE WHEN e.event_name = 'dedicated_user_first_login'
                         THEN e.event_timestamp END) AS step_2_at,
                MIN(CASE WHEN e.event_name = 'dedicated_onboarding_step_completed'
                         THEN e.event_timestamp END) AS step_3_at,
                MIN(CASE WHEN e.event_name = 'dedicated_project_created'
                         THEN e.event_timestamp END) AS step_4_at,
                MIN(CASE WHEN e.event_name = 'dedicated_pipeline_executed'
                         THEN e.event_timestamp END) AS step_5_at,
                MIN(CASE WHEN e.event_name = 'dedicated_onboarding_completed'
                         THEN e.event_timestamp END) AS step_6_at,
                MIN(CASE WHEN e.event_name = 'dedicated_user_activated'
                         THEN e.event_timestamp END) AS step_7_at
            FROM invited i
            LEFT JOIN raw.dedicated_events e
                ON e.user_id = i.user_id
               AND e.tenant_id = i.tenant_id
               AND e.event_timestamp >= i.invited_at
            GROUP BY i.user_id, i.tenant_id, i.invited_at
        )
        SELECT
            COUNT(*) AS step_0_invited,
            COUNT(step_1_at) AS step_1_accepted,
            COUNT(step_2_at) AS step_2_first_login,
            COUNT(step_3_at) AS step_3_onboarding_step,
            COUNT(step_4_at) AS step_4_first_project,
            COUNT(step_5_at) AS step_5_first_pipeline,
            COUNT(step_6_at) AS step_6_completed,
            COUNT(step_7_at) AS step_7_activated
        FROM step_completions
    """).fetchdf()
    con.close()

    # Build funnel table
    steps = [
        ("Invitation Sent",     int(df["step_0_invited"].iloc[0])),
        ("Invitation Accepted", int(df["step_1_accepted"].iloc[0])),
        ("First Login",         int(df["step_2_first_login"].iloc[0])),
        ("Onboarding Step",     int(df["step_3_onboarding_step"].iloc[0])),
        ("First Project",       int(df["step_4_first_project"].iloc[0])),
        ("First Pipeline",      int(df["step_5_first_pipeline"].iloc[0])),
        ("Onboarding Complete", int(df["step_6_completed"].iloc[0])),
        ("Activated",           int(df["step_7_activated"].iloc[0])),
    ]

    table = Table(title="Onboarding Funnel Results", show_lines=True)
    table.add_column("Step", style="bold")
    table.add_column("Users", justify="right")
    table.add_column("Conversion %", justify="right")
    table.add_column("Drop-off %", justify="right")
    table.add_column("Bar", min_width=20)
    table.add_column("Benchmark", justify="right")

    benchmarks = list(FUNNEL_BENCHMARKS.values())
    funnel_rows = []
    for i, (name, count) in enumerate(steps):
        prev_count = steps[i - 1][1] if i > 0 else count
        cvr = (count / prev_count * 100) if prev_count > 0 else 0
        dropoff = 100 - cvr if i > 0 else 0
        bar_len = int(count / steps[0][1] * 20) if steps[0][1] > 0 else 0
        bar = "█" * bar_len + "░" * (20 - bar_len)
        benchmark = f"{benchmarks[i-1]*100:.0f}%" if 0 < i < len(benchmarks) + 1 else "—"

        cvr_str = f"{cvr:.1f}%" if i > 0 else "—"
        dropoff_str = f"{dropoff:.1f}%" if i > 0 else "—"

        # Color coding
        if i > 0 and dropoff > 35:
            cvr_str = f"[bold red]{cvr_str}[/]"
            dropoff_str = f"[bold red]{dropoff_str}[/]"
        elif i > 0 and dropoff > 20:
            cvr_str = f"[yellow]{cvr_str}[/]"
            dropoff_str = f"[yellow]{dropoff_str}[/]"
        else:
            cvr_str = f"[green]{cvr_str}[/]"

        table.add_row(f"{i}. {name}", str(count), cvr_str, dropoff_str, bar, benchmark)

        funnel_rows.append({
            "step_number": i,
            "step_name": name,
            "users": count,
            "conversion_pct": round(cvr, 1),
            "dropoff_pct": round(dropoff, 1),
        })

    console.print(table)

    # E2E conversion
    e2e = steps[-1][1] / steps[0][1] * 100 if steps[0][1] > 0 else 0
    console.print(f"\n  End-to-end conversion (Invited → Activated): [bold]{e2e:.1f}%[/]")
    console.print(f"  Target (30% improvement): [bold green]{e2e * 1.3:.1f}%[/]\n")

    return pd.DataFrame(funnel_rows)


def compute_time_to_complete():
    """Compute median time-to-complete for each funnel transition."""
    console.print("[bold cyan]▶ Time-to-Complete per Funnel Step[/]")
    con = duckdb.connect(DB_PATH, read_only=True)

    df = con.execute("""
        WITH invited AS (
            SELECT DISTINCT user_id, tenant_id, MIN(event_timestamp) AS invited_at
            FROM raw.dedicated_events
            WHERE event_name = 'dedicated_user_invited'
            GROUP BY user_id, tenant_id
        ),
        steps AS (
            SELECT
                i.user_id,
                i.invited_at,
                MIN(CASE WHEN e.event_name = 'dedicated_user_invitation_accepted'
                         THEN e.event_timestamp END) AS step_1,
                MIN(CASE WHEN e.event_name = 'dedicated_user_first_login'
                         THEN e.event_timestamp END) AS step_2,
                MIN(CASE WHEN e.event_name = 'dedicated_onboarding_step_completed'
                         THEN e.event_timestamp END) AS step_3,
                MIN(CASE WHEN e.event_name = 'dedicated_project_created'
                         THEN e.event_timestamp END) AS step_4,
                MIN(CASE WHEN e.event_name = 'dedicated_pipeline_executed'
                         THEN e.event_timestamp END) AS step_5,
                MIN(CASE WHEN e.event_name = 'dedicated_onboarding_completed'
                         THEN e.event_timestamp END) AS step_6,
                MIN(CASE WHEN e.event_name = 'dedicated_user_activated'
                         THEN e.event_timestamp END) AS step_7
            FROM invited i
            LEFT JOIN raw.dedicated_events e
                ON e.user_id = i.user_id AND e.tenant_id = i.tenant_id
            GROUP BY i.user_id, i.invited_at
        )
        SELECT
            'Invite → Accept' AS transition,
            ROUND(MEDIAN(EXTRACT(EPOCH FROM (step_1 - invited_at)) / 60), 1) AS median_minutes,
            ROUND(QUANTILE_CONT(EXTRACT(EPOCH FROM (step_1 - invited_at)) / 60, 0.9), 1) AS p90_minutes
        FROM steps WHERE step_1 IS NOT NULL
        UNION ALL
        SELECT 'Accept → Login',
            ROUND(MEDIAN(EXTRACT(EPOCH FROM (step_2 - step_1)) / 60), 1),
            ROUND(QUANTILE_CONT(EXTRACT(EPOCH FROM (step_2 - step_1)) / 60, 0.9), 1)
        FROM steps WHERE step_2 IS NOT NULL AND step_1 IS NOT NULL
        UNION ALL
        SELECT 'Login → Onboarding',
            ROUND(MEDIAN(EXTRACT(EPOCH FROM (step_3 - step_2)) / 60), 1),
            ROUND(QUANTILE_CONT(EXTRACT(EPOCH FROM (step_3 - step_2)) / 60, 0.9), 1)
        FROM steps WHERE step_3 IS NOT NULL AND step_2 IS NOT NULL
        UNION ALL
        SELECT 'Onboarding → Project',
            ROUND(MEDIAN(EXTRACT(EPOCH FROM (step_4 - step_3)) / 60), 1),
            ROUND(QUANTILE_CONT(EXTRACT(EPOCH FROM (step_4 - step_3)) / 60, 0.9), 1)
        FROM steps WHERE step_4 IS NOT NULL AND step_3 IS NOT NULL
        UNION ALL
        SELECT 'Project → Pipeline',
            ROUND(MEDIAN(EXTRACT(EPOCH FROM (step_5 - step_4)) / 60), 1),
            ROUND(QUANTILE_CONT(EXTRACT(EPOCH FROM (step_5 - step_4)) / 60, 0.9), 1)
        FROM steps WHERE step_5 IS NOT NULL AND step_4 IS NOT NULL
        UNION ALL
        SELECT 'Pipeline → Complete',
            ROUND(MEDIAN(EXTRACT(EPOCH FROM (step_6 - step_5)) / 60), 1),
            ROUND(QUANTILE_CONT(EXTRACT(EPOCH FROM (step_6 - step_5)) / 60, 0.9), 1)
        FROM steps WHERE step_6 IS NOT NULL AND step_5 IS NOT NULL
        UNION ALL
        SELECT 'Complete → Activated',
            ROUND(MEDIAN(EXTRACT(EPOCH FROM (step_7 - step_6)) / 3600), 1),
            ROUND(QUANTILE_CONT(EXTRACT(EPOCH FROM (step_7 - step_6)) / 3600, 0.9), 1)
        FROM steps WHERE step_7 IS NOT NULL AND step_6 IS NOT NULL
    """).fetchdf()
    con.close()

    table = Table(title="Time-to-Complete per Step", show_lines=True)
    table.add_column("Transition", style="bold")
    table.add_column("Median", justify="right")
    table.add_column("P90", justify="right")
    table.add_column("Unit")

    for _, row in df.iterrows():
        unit = "hours" if "Activated" in str(row["transition"]) else "min"
        median_val = row["median_minutes"] if row["median_minutes"] is not None else 0
        p90_val = row["p90_minutes"] if row["p90_minutes"] is not None else 0
        table.add_row(
            str(row["transition"]),
            f"{median_val:.1f}",
            f"{p90_val:.1f}",
            unit,
        )
    console.print(table)
    console.print()

    return df


def compute_segment_analysis():
    """Analyze funnel conversion by user segments."""
    console.print("[bold cyan]▶ Funnel Segmentation — By User Role[/]")
    con = duckdb.connect(DB_PATH, read_only=True)

    df = con.execute("""
        WITH invited AS (
            SELECT DISTINCT
                r.user_id,
                r.tenant_id,
                MIN(r.event_timestamp) AS invited_at,
                u.role
            FROM raw.dedicated_events r
            JOIN analytics.dim_users u ON r.user_id = u.user_id AND u.is_current = TRUE
            WHERE r.event_name = 'dedicated_user_invited'
            GROUP BY r.user_id, r.tenant_id, u.role
        ),
        completions AS (
            SELECT
                i.user_id,
                i.role,
                COUNT(DISTINCT CASE WHEN e.event_name = 'dedicated_user_first_login' THEN 1 END) AS logged_in,
                COUNT(DISTINCT CASE WHEN e.event_name = 'dedicated_onboarding_completed' THEN 1 END) AS completed,
                COUNT(DISTINCT CASE WHEN e.event_name = 'dedicated_user_activated' THEN 1 END) AS activated
            FROM invited i
            LEFT JOIN raw.dedicated_events e
                ON e.user_id = i.user_id AND e.tenant_id = i.tenant_id
            GROUP BY i.user_id, i.role
        )
        SELECT
            role,
            COUNT(*) AS invited,
            SUM(logged_in) AS logged_in,
            SUM(completed) AS completed,
            SUM(activated) AS activated,
            ROUND(SUM(logged_in) * 100.0 / COUNT(*), 1) AS login_rate,
            ROUND(SUM(completed) * 100.0 / NULLIF(SUM(logged_in), 0), 1) AS completion_rate,
            ROUND(SUM(activated) * 100.0 / COUNT(*), 1) AS activation_rate
        FROM completions
        GROUP BY role
        ORDER BY activation_rate DESC
    """).fetchdf()
    con.close()

    table = Table(title="Funnel Performance by Role", show_lines=True)
    table.add_column("Role", style="bold")
    table.add_column("Invited", justify="right")
    table.add_column("Logged In", justify="right")
    table.add_column("Completed", justify="right")
    table.add_column("Activated", justify="right")
    table.add_column("Login %", justify="right")
    table.add_column("Activation %", justify="right")

    for _, row in df.iterrows():
        act_rate = row["activation_rate"] if row["activation_rate"] is not None else 0
        act_color = "green" if act_rate >= 15 else "yellow" if act_rate >= 10 else "red"
        table.add_row(
            str(row["role"]),
            str(int(row["invited"])),
            str(int(row["logged_in"])),
            str(int(row["completed"])),
            str(int(row["activated"])),
            f"{row['login_rate']:.1f}%",
            f"[{act_color}]{act_rate:.1f}%[/{act_color}]",
        )
    console.print(table)
    console.print()

    return df


def compute_cohort_analysis():
    """Analyze funnel performance by invitation week cohort."""
    console.print("[bold cyan]▶ Cohort Analysis — By Invitation Week[/]")
    con = duckdb.connect(DB_PATH, read_only=True)

    df = con.execute("""
        WITH invited AS (
            SELECT DISTINCT
                user_id, tenant_id,
                MIN(event_timestamp) AS invited_at,
                DATE_TRUNC('week', MIN(event_timestamp)) AS cohort_week
            FROM raw.dedicated_events
            WHERE event_name = 'dedicated_user_invited'
            GROUP BY user_id, tenant_id
        ),
        steps AS (
            SELECT
                i.user_id,
                i.cohort_week,
                COUNT(DISTINCT CASE WHEN e.event_name = 'dedicated_user_invitation_accepted' THEN 1 END) AS accepted,
                COUNT(DISTINCT CASE WHEN e.event_name = 'dedicated_user_first_login' THEN 1 END) AS logged_in,
                COUNT(DISTINCT CASE WHEN e.event_name = 'dedicated_onboarding_completed' THEN 1 END) AS completed,
                COUNT(DISTINCT CASE WHEN e.event_name = 'dedicated_user_activated' THEN 1 END) AS activated
            FROM invited i
            LEFT JOIN raw.dedicated_events e
                ON e.user_id = i.user_id AND e.tenant_id = i.tenant_id
            GROUP BY i.user_id, i.cohort_week
        )
        SELECT
            cohort_week,
            COUNT(*) AS invited,
            SUM(accepted) AS accepted,
            SUM(logged_in) AS logged_in,
            SUM(completed) AS completed,
            SUM(activated) AS activated,
            ROUND(SUM(accepted) * 100.0 / COUNT(*), 1) AS accept_rate,
            ROUND(SUM(activated) * 100.0 / COUNT(*), 1) AS activation_rate
        FROM steps
        GROUP BY cohort_week
        ORDER BY cohort_week
    """).fetchdf()
    con.close()

    table = Table(title="Weekly Cohort Performance", show_lines=True)
    table.add_column("Cohort Week", style="bold")
    table.add_column("Invited", justify="right")
    table.add_column("Accepted", justify="right")
    table.add_column("Logged In", justify="right")
    table.add_column("Completed", justify="right")
    table.add_column("Activated", justify="right")
    table.add_column("Accept %", justify="right")
    table.add_column("Activation %", justify="right")

    for _, row in df.iterrows():
        table.add_row(
            str(row["cohort_week"])[:10],
            str(int(row["invited"])),
            str(int(row["accepted"])),
            str(int(row["logged_in"])),
            str(int(row["completed"])),
            str(int(row["activated"])),
            f"{row['accept_rate']:.1f}%",
            f"{row['activation_rate']:.1f}%",
        )
    console.print(table)
    console.print()

    return df


if __name__ == "__main__":
    run_funnel_analysis()
