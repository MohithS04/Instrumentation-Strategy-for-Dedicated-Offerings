-- =============================================================================
-- SQL VALIDATION QUERIES — GitLab Dedicated Event Pipeline
-- =============================================================================
-- Purpose:  Reusable SQL templates for validating data integrity across
--           the raw → transformed → BI pipeline.
-- Target:   Snowflake (compatible with BigQuery/Redshift with minor syntax adjustments)
-- Version:  1.0 | 2026-03-16
-- =============================================================================


-- =============================================================================
-- QUERY 1: ROW COUNT RECONCILIATION — Raw vs. Transformed Tables
-- =============================================================================
-- Description: Compares distinct event counts between the raw landing table
--              and the transformed analytics fact table to detect data loss
--              or duplication introduced during transformation.
--
-- Expected Result: variance_pct <= 0.1% → PASS
-- =============================================================================

WITH raw_summary AS (
    SELECT
        event_name,
        DATE(event_timestamp)                     AS event_date,
        COUNT(*)                                  AS total_raw_rows,
        COUNT(DISTINCT event_id)                  AS distinct_raw_events
    FROM raw.dedicated_events
    WHERE event_timestamp >= :start_date
      AND event_timestamp <  :end_date
    GROUP BY event_name, DATE(event_timestamp)
),

transformed_summary AS (
    SELECT
        event_name,
        event_date,
        COUNT(*)                                  AS total_transformed_rows,
        COUNT(DISTINCT event_id)                  AS distinct_transformed_events
    FROM analytics.fct_dedicated_events
    WHERE event_date >= :start_date
      AND event_date <  :end_date
    GROUP BY event_name, event_date
)

SELECT
    COALESCE(r.event_name, t.event_name)          AS event_name,
    COALESCE(r.event_date, t.event_date)          AS event_date,
    r.total_raw_rows,
    t.total_transformed_rows,
    r.distinct_raw_events,
    t.distinct_transformed_events,
    -- Absolute difference
    COALESCE(r.distinct_raw_events, 0)
        - COALESCE(t.distinct_transformed_events, 0)
                                                  AS event_count_diff,
    -- Variance percentage
    CASE
        WHEN COALESCE(r.distinct_raw_events, 0) = 0 THEN NULL
        ELSE ROUND(
            ABS(
                COALESCE(r.distinct_raw_events, 0)
                - COALESCE(t.distinct_transformed_events, 0)
            ) * 100.0 / r.distinct_raw_events, 4)
    END                                           AS variance_pct,
    -- Pass/Fail verdict
    CASE
        WHEN COALESCE(r.distinct_raw_events, 0) = 0
         AND COALESCE(t.distinct_transformed_events, 0) > 0
            THEN 'FAIL — Orphan rows in transformed layer'
        WHEN COALESCE(t.distinct_transformed_events, 0) = 0
         AND COALESCE(r.distinct_raw_events, 0) > 0
            THEN 'FAIL — Events missing from transformed layer'
        WHEN ABS(
                COALESCE(r.distinct_raw_events, 0)
                - COALESCE(t.distinct_transformed_events, 0)
             ) * 100.0 / NULLIF(r.distinct_raw_events, 0) > 0.1
            THEN 'WARN — Variance exceeds 0.1% threshold'
        ELSE 'PASS'
    END                                           AS validation_result
FROM raw_summary r
FULL OUTER JOIN transformed_summary t
    ON  r.event_name = t.event_name
    AND r.event_date = t.event_date
ORDER BY validation_result DESC, event_date, event_name;


-- =============================================================================
-- QUERY 2: NULL / MISSING PROPERTY CHECKS ON CRITICAL EVENT FIELDS
-- =============================================================================
-- Description: Scans the raw events table for NULL or empty values in fields
--              that are defined as REQUIRED in the Event Taxonomy.
--
-- Critical Fields Checked:
--   event_id, tenant_id, user_id, timestamp, event_name, platform_version
--
-- Expected Result: All null_* columns = 0 for every event_name
-- =============================================================================

SELECT
    event_name,
    DATE(event_timestamp)                         AS event_date,
    COUNT(*)                                      AS total_events,

    -- Null checks on required fields
    SUM(CASE WHEN event_id         IS NULL OR event_id = ''
             THEN 1 ELSE 0 END)                  AS null_event_id,
    SUM(CASE WHEN tenant_id        IS NULL OR tenant_id = ''
             THEN 1 ELSE 0 END)                  AS null_tenant_id,
    SUM(CASE WHEN user_id          IS NULL OR user_id = ''
             THEN 1 ELSE 0 END)                  AS null_user_id,
    SUM(CASE WHEN event_timestamp  IS NULL
             THEN 1 ELSE 0 END)                  AS null_timestamp,
    SUM(CASE WHEN event_name       IS NULL OR event_name = ''
             THEN 1 ELSE 0 END)                  AS null_event_name,
    SUM(CASE WHEN platform_version IS NULL OR platform_version = ''
             THEN 1 ELSE 0 END)                  AS null_platform_version,
    SUM(CASE WHEN session_id       IS NULL OR session_id = ''
             THEN 1 ELSE 0 END)                  AS null_session_id,
    SUM(CASE WHEN event_source     IS NULL OR event_source = ''
             THEN 1 ELSE 0 END)                  AS null_event_source,

    -- Overall quality score
    ROUND(
        (
            SUM(CASE WHEN event_id IS NULL OR event_id = '' THEN 1 ELSE 0 END) +
            SUM(CASE WHEN tenant_id IS NULL OR tenant_id = '' THEN 1 ELSE 0 END) +
            SUM(CASE WHEN user_id IS NULL OR user_id = '' THEN 1 ELSE 0 END) +
            SUM(CASE WHEN event_timestamp IS NULL THEN 1 ELSE 0 END) +
            SUM(CASE WHEN platform_version IS NULL OR platform_version = '' THEN 1 ELSE 0 END)
        ) * 100.0 / (COUNT(*) * 5), 4
    )                                             AS null_rate_pct,

    CASE
        WHEN (
            SUM(CASE WHEN event_id IS NULL OR event_id = '' THEN 1 ELSE 0 END) +
            SUM(CASE WHEN tenant_id IS NULL OR tenant_id = '' THEN 1 ELSE 0 END) +
            SUM(CASE WHEN user_id IS NULL OR user_id = '' THEN 1 ELSE 0 END) +
            SUM(CASE WHEN event_timestamp IS NULL THEN 1 ELSE 0 END) +
            SUM(CASE WHEN platform_version IS NULL OR platform_version = '' THEN 1 ELSE 0 END)
        ) > 0
            THEN 'FAIL — Required fields have NULL values'
        ELSE 'PASS'
    END                                           AS validation_result

FROM raw.dedicated_events
WHERE event_timestamp >= :start_date
  AND event_timestamp <  :end_date
GROUP BY event_name, DATE(event_timestamp)
HAVING (
    SUM(CASE WHEN event_id IS NULL OR event_id = '' THEN 1 ELSE 0 END) +
    SUM(CASE WHEN tenant_id IS NULL OR tenant_id = '' THEN 1 ELSE 0 END) +
    SUM(CASE WHEN user_id IS NULL OR user_id = '' THEN 1 ELSE 0 END) +
    SUM(CASE WHEN event_timestamp IS NULL THEN 1 ELSE 0 END) +
    SUM(CASE WHEN platform_version IS NULL OR platform_version = '' THEN 1 ELSE 0 END)
) > 0
ORDER BY null_rate_pct DESC, event_date;


-- =============================================================================
-- QUERY 3: DUPLICATE EVENT DETECTION USING event_id DEDUPLICATION
-- =============================================================================
-- Description: Identifies duplicate events in the raw table. Duplicates are
--              defined as multiple rows sharing the same event_id.
--
--              This can occur due to: client retry logic, collector replay,
--              pipeline re-ingestion, or SDK double-fire.
--
-- Expected Result: Row count of this query should be 0 (no duplicates).
-- =============================================================================

WITH duplicate_events AS (
    SELECT
        event_id,
        event_name,
        tenant_id,
        user_id,
        COUNT(*)                                  AS occurrence_count,
        MIN(event_timestamp)                      AS first_seen,
        MAX(event_timestamp)                      AS last_seen,
        DATEDIFF('second', MIN(event_timestamp), MAX(event_timestamp))
                                                  AS time_span_seconds
    FROM raw.dedicated_events
    WHERE event_timestamp >= :start_date
      AND event_timestamp <  :end_date
    GROUP BY event_id, event_name, tenant_id, user_id
    HAVING COUNT(*) > 1
)

SELECT
    d.event_name,
    d.tenant_id,
    COUNT(DISTINCT d.event_id)                    AS duplicate_event_count,
    SUM(d.occurrence_count)                       AS total_duplicate_rows,
    SUM(d.occurrence_count) - COUNT(DISTINCT d.event_id)
                                                  AS excess_rows,
    AVG(d.time_span_seconds)                      AS avg_time_span_seconds,
    MAX(d.occurrence_count)                        AS max_occurrences,

    -- Impact assessment
    ROUND(
        (SUM(d.occurrence_count) - COUNT(DISTINCT d.event_id))
        * 100.0 / NULLIF(
            (SELECT COUNT(*) FROM raw.dedicated_events
             WHERE event_timestamp >= :start_date
               AND event_timestamp <  :end_date
               AND event_name = d.event_name
               AND tenant_id = d.tenant_id), 0
        ), 4
    )                                             AS duplicate_rate_pct,

    CASE
        WHEN AVG(d.time_span_seconds) < 2
            THEN 'Likely: Client retry / double fire'
        WHEN AVG(d.time_span_seconds) BETWEEN 2 AND 300
            THEN 'Likely: Collector replay'
        ELSE 'Likely: Pipeline re-ingestion'
    END                                           AS probable_cause

FROM duplicate_events d
GROUP BY d.event_name, d.tenant_id
ORDER BY total_duplicate_rows DESC;


-- =============================================================================
-- QUERY 4 (BONUS): TENANT-LEVEL EVENT COVERAGE CHECK
-- =============================================================================
-- Description: Verifies that all active tenants are reporting the expected
--              set of P0 events. Surfaces tenants with gaps in instrumentation
--              (e.g., opted out, SDK misconfigured, or version mismatch).
-- =============================================================================

WITH expected_p0_events AS (
    SELECT event_name FROM (VALUES
        ('dedicated_tenant_provisioned'),
        ('dedicated_user_invited'),
        ('dedicated_onboarding_step_completed'),
        ('dedicated_pipeline_executed'),
        ('dedicated_sso_configured')
    ) AS t(event_name)
),

active_tenants AS (
    SELECT DISTINCT tenant_id
    FROM raw.dedicated_events
    WHERE event_timestamp >= :start_date
      AND event_timestamp <  :end_date
),

tenant_event_matrix AS (
    SELECT
        t.tenant_id,
        e.event_name,
        COUNT(r.event_id)                         AS event_count
    FROM active_tenants t
    CROSS JOIN expected_p0_events e
    LEFT JOIN raw.dedicated_events r
        ON  r.tenant_id   = t.tenant_id
        AND r.event_name  = e.event_name
        AND r.event_timestamp >= :start_date
        AND r.event_timestamp <  :end_date
    GROUP BY t.tenant_id, e.event_name
)

SELECT
    tenant_id,
    event_name,
    event_count,
    CASE
        WHEN event_count = 0 THEN 'MISSING — P0 event not reported'
        ELSE 'OK'
    END                                           AS coverage_status
FROM tenant_event_matrix
WHERE event_count = 0
ORDER BY tenant_id, event_name;
