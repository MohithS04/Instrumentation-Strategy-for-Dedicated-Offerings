"""
Main Orchestrator — GitLab Dedicated Instrumentation Strategy Pipeline
=====================================================================
Executes all four workstreams end-to-end:
  1. Generate synthetic data (tenants, users, events)
  2. Load into DuckDB (raw + analytics schemas)
  3. Run data validation & reconciliation (Workstream 2)
  4. Run onboarding funnel analysis (Workstream 3)
  5. Generate reports & visualizations
"""
import os
import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

BANNER = """
 ╔═══════════════════════════════════════════════════════════════════╗
 ║   GitLab Dedicated — Instrumentation Strategy Pipeline          ║
 ║   Workstreams 1–4 | Data Generation → Validation → Analysis     ║
 ╚═══════════════════════════════════════════════════════════════════╝
"""


def main():
    start_time = time.time()
    console.print(Text(BANNER, style="bold cyan"))

    # ─────────────────────────────────────────────────
    # PHASE 1: Data Generation
    # ─────────────────────────────────────────────────
    console.print(Panel("[bold]PHASE 1: Synthetic Data Generation[/]",
                        style="bold blue", expand=False))

    from data_generator import generate_tenants, generate_users, generate_events

    tenants = generate_tenants()
    users = generate_users(tenants)
    events = generate_events(tenants, users)

    console.print(f"  [green]✓[/] Generated [bold]{len(tenants)}[/] tenants")
    console.print(f"  [green]✓[/] Generated [bold]{len(users)}[/] users")
    console.print(f"  [green]✓[/] Generated [bold]{len(events):,}[/] events "
                  f"(including deliberate quality issues)")
    console.print()

    # ─────────────────────────────────────────────────
    # PHASE 2: Database Setup & Data Loading
    # ─────────────────────────────────────────────────
    console.print(Panel("[bold]PHASE 2: Database Setup & Data Loading[/]",
                        style="bold blue", expand=False))

    from db_setup import init_database, load_data

    init_database()
    load_data(tenants, users, events)
    console.print()

    # ─────────────────────────────────────────────────
    # PHASE 3: Data Validation (Workstream 2)
    # ─────────────────────────────────────────────────
    console.print(Panel("[bold]PHASE 3: Data Validation & Reconciliation (WS2)[/]",
                        style="bold blue", expand=False))

    from validation_engine import run_all_validations
    validation_results = run_all_validations()

    # ─────────────────────────────────────────────────
    # PHASE 4: Funnel Analysis (Workstream 3)
    # ─────────────────────────────────────────────────
    console.print(Panel("[bold]PHASE 4: Onboarding Funnel Analysis (WS3)[/]",
                        style="bold blue", expand=False))

    from funnel_analysis import run_funnel_analysis
    funnel_results = run_funnel_analysis()

    # ─────────────────────────────────────────────────
    # PHASE 5: Report Generation
    # ─────────────────────────────────────────────────
    console.print(Panel("[bold]PHASE 5: Report & Visualization Generation[/]",
                        style="bold blue", expand=False))

    from report_generator import generate_all_reports
    generate_all_reports(validation_results, funnel_results)

    # ─────────────────────────────────────────────────
    # PHASE 6: Summary
    # ─────────────────────────────────────────────────
    elapsed = time.time() - start_time

    from config import OUTPUT_DIR, DB_PATH

    summary = f"""
[bold green]Pipeline Complete![/]

[bold]Data Generated:[/]
  • {len(tenants)} tenants across {len(set(t['region'] for t in tenants))} regions
  • {len(users)} users with lifecycle simulation
  • {len(events):,} raw events (with quality issues for testing)

[bold]Validation Results (WS2):[/]
  • Row count reconciliation: raw vs. BI layer
  • Null/missing field detection on critical properties
  • Duplicate event identification & deduplication
  • P0 event coverage check across all tenants

[bold]Funnel Analysis (WS3):[/]
  • 8-step onboarding funnel with conversion rates
  • Time-to-complete per transition step
  • Role-based segmentation analysis
  • Weekly cohort trend analysis

[bold]Outputs:[/]
  • Database: {DB_PATH}
  • Excel Report: {os.path.join(OUTPUT_DIR, 'reports', 'instrumentation_strategy_report.xlsx')}
  • Charts: {os.path.join(OUTPUT_DIR, 'charts/')}

[dim]Completed in {elapsed:.1f} seconds[/]
"""
    console.print(Panel(summary, title="[bold cyan]Execution Summary[/]",
                        border_style="green", expand=False))


if __name__ == "__main__":
    main()
