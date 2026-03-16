"""
Module 2: Database Setup & Data Loading
Creates DuckDB schemas and loads synthetic data.
"""
import json
import duckdb
from rich.console import Console
from config import DB_PATH

console = Console()


def init_database():
    """Create database and schemas."""
    con = duckdb.connect(DB_PATH)

    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("CREATE SCHEMA IF NOT EXISTS analytics")

    # --- Raw Events Table ---
    con.execute("""
        CREATE OR REPLACE TABLE raw.dedicated_events (
            event_id            VARCHAR NOT NULL,
            event_name          VARCHAR NOT NULL,
            event_category      VARCHAR,
            tenant_id           VARCHAR NOT NULL,
            user_id             VARCHAR,
            session_id          VARCHAR,
            event_timestamp     TIMESTAMP NOT NULL,
            collector_tstamp    TIMESTAMP NOT NULL,
            loaded_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            platform_version    VARCHAR,
            event_source        VARCHAR NOT NULL,
            properties          VARCHAR,
            sdk_version         VARCHAR
        )
    """)

    # --- Analytics Fact Table (deduplicated, enriched) ---
    con.execute("""
        CREATE OR REPLACE TABLE analytics.fct_dedicated_events (
            event_key           INTEGER,
            event_id            VARCHAR NOT NULL,
            event_name          VARCHAR NOT NULL,
            event_category      VARCHAR NOT NULL,
            tenant_id           VARCHAR NOT NULL,
            user_id             VARCHAR,
            session_id          VARCHAR,
            event_timestamp     TIMESTAMP NOT NULL,
            event_date          DATE NOT NULL,
            event_hour          INTEGER NOT NULL,
            event_day_of_week   INTEGER NOT NULL,
            platform_version    VARCHAR,
            event_source        VARCHAR NOT NULL,
            step_name           VARCHAR,
            step_index          INTEGER,
            project_id          VARCHAR,
            pipeline_id         VARCHAR,
            pipeline_status     VARCHAR,
            scan_type           VARCHAR,
            duration_seconds    INTEGER,
            properties_json     VARCHAR,
            loaded_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- Dimension: Tenants ---
    con.execute("""
        CREATE OR REPLACE TABLE analytics.dim_tenants (
            tenant_surrogate_key INTEGER,
            tenant_id           VARCHAR NOT NULL,
            tenant_name         VARCHAR NOT NULL,
            region              VARCHAR NOT NULL,
            plan_tier           VARCHAR NOT NULL,
            seat_limit          INTEGER NOT NULL,
            sso_enabled         BOOLEAN NOT NULL DEFAULT FALSE,
            provisioning_date   DATE NOT NULL,
            valid_from          TIMESTAMP NOT NULL,
            valid_to            TIMESTAMP,
            is_current          BOOLEAN NOT NULL DEFAULT TRUE,
            loaded_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- Dimension: Users ---
    con.execute("""
        CREATE OR REPLACE TABLE analytics.dim_users (
            user_surrogate_key  INTEGER,
            user_id             VARCHAR NOT NULL,
            tenant_id           VARCHAR NOT NULL,
            role                VARCHAR NOT NULL,
            is_active           BOOLEAN NOT NULL DEFAULT TRUE,
            invite_date         DATE,
            first_login_date    DATE,
            activation_date     DATE,
            onboarding_status   VARCHAR,
            valid_from          TIMESTAMP NOT NULL,
            valid_to            TIMESTAMP,
            is_current          BOOLEAN NOT NULL DEFAULT TRUE,
            loaded_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    con.close()
    console.print("[bold green]✓[/] Database schemas created successfully")
    return True


def load_data(tenants, users, events):
    """Load generated data into DuckDB."""
    con = duckdb.connect(DB_PATH)

    # --- Load Tenants ---
    for i, t in enumerate(tenants):
        con.execute("""
            INSERT INTO analytics.dim_tenants VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            i + 1, t["tenant_id"], t["tenant_name"], t["region"],
            t["plan_tier"], t["seat_limit"], t["sso_enabled"],
            t["provisioning_date"], t["valid_from"], t["valid_to"], t["is_current"],
        ])
    console.print(f"  [cyan]→[/] Loaded {len(tenants)} tenants into dim_tenants")

    # --- Load Users ---
    for i, u in enumerate(users):
        con.execute("""
            INSERT INTO analytics.dim_users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            i + 1, u["user_id"], u["tenant_id"], u["role"], u["is_active"],
            u["invite_date"], u["first_login_date"], u["activation_date"],
            u["onboarding_status"], u["valid_from"], u["valid_to"], u["is_current"],
        ])
    console.print(f"  [cyan]→[/] Loaded {len(users)} users into dim_users")

    # --- Load Raw Events ---
    for evt in events:
        con.execute("""
            INSERT INTO raw.dedicated_events
            (event_id, event_name, event_category, tenant_id, user_id, session_id,
             event_timestamp, collector_tstamp, platform_version, event_source,
             properties, sdk_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            evt["event_id"], evt["event_name"], evt["event_category"],
            evt["tenant_id"], evt["user_id"], evt["session_id"],
            evt["event_timestamp"], evt["collector_tstamp"],
            evt["platform_version"], evt["event_source"],
            json.dumps(evt["properties"]), evt.get("sdk_version"),
        ])
    console.print(f"  [cyan]→[/] Loaded {len(events)} events into raw.dedicated_events")

    # --- Transform: Build fact table (deduplicated) ---
    con.execute("""
        INSERT INTO analytics.fct_dedicated_events
        SELECT
            ROW_NUMBER() OVER (ORDER BY event_timestamp)    AS event_key,
            event_id,
            event_name,
            COALESCE(event_category, 'unknown')             AS event_category,
            tenant_id,
            user_id,
            session_id,
            event_timestamp,
            CAST(event_timestamp AS DATE)                   AS event_date,
            EXTRACT(HOUR FROM event_timestamp)              AS event_hour,
            EXTRACT(DOW FROM event_timestamp)               AS event_day_of_week,
            platform_version,
            event_source,
            CASE WHEN event_name = 'dedicated_onboarding_step_completed'
                 THEN json_extract_string(properties, '$.step_name')
                 ELSE NULL END                              AS step_name,
            CASE WHEN event_name = 'dedicated_onboarding_step_completed'
                 THEN CAST(json_extract_string(properties, '$.step_index') AS INTEGER)
                 ELSE NULL END                              AS step_index,
            json_extract_string(properties, '$.project_id') AS project_id,
            json_extract_string(properties, '$.pipeline_id') AS pipeline_id,
            json_extract_string(properties, '$.status')     AS pipeline_status,
            json_extract_string(properties, '$.scan_type')  AS scan_type,
            CAST(json_extract_string(properties, '$.duration_seconds') AS INTEGER) AS duration_seconds,
            properties                                      AS properties_json,
            CURRENT_TIMESTAMP                               AS loaded_at
        FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY collector_tstamp) AS rn
            FROM raw.dedicated_events
        )
        WHERE rn = 1
    """)

    fct_count = con.execute("SELECT COUNT(*) FROM analytics.fct_dedicated_events").fetchone()[0]
    console.print(f"  [cyan]→[/] Built fact table with {fct_count} deduplicated events")

    con.close()
    return True


if __name__ == "__main__":
    init_database()
