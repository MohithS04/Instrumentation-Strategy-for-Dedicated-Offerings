-- =============================================================================
-- SCHEMA DESIGN — GitLab Dedicated Core Events & Dimension Tables
-- =============================================================================
-- Target:   Snowflake (compatible with PostgreSQL/BigQuery with minor adjustments)
-- Purpose:  Production-ready DDL for the analytics layer supporting GitLab
--           Dedicated product instrumentation.
-- Version:  1.0 | 2026-03-16
-- =============================================================================


-- =============================================================================
-- 1. RAW EVENTS TABLE (Landing Zone)
-- =============================================================================
-- Description: Raw events as received from the Snowplow collector / ingestion
--              API. This is the source-of-truth table before any transformation.
-- Grain:      One row per raw event payload received.
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw.dedicated_events (
    -- Primary identifier
    event_id            VARCHAR(36)     NOT NULL    COMMENT 'Globally unique event identifier (UUID v4)',

    -- Event classification
    event_name          VARCHAR(60)     NOT NULL    COMMENT 'Event name from the Dedicated taxonomy (snake_case)',
    event_category      VARCHAR(30)     NULL        COMMENT 'Logical category: onboarding, feature_adoption, admin, navigation, etc.',

    -- Entity references
    tenant_id           VARCHAR(36)     NOT NULL    COMMENT 'Dedicated tenant instance identifier',
    user_id             VARCHAR(36)     NOT NULL    COMMENT 'Anonymized user identifier (not PII)',
    session_id          VARCHAR(36)     NULL        COMMENT 'Browser/API session ID (null for server-side-only events)',

    -- Timestamps
    event_timestamp     TIMESTAMP_TZ    NOT NULL    COMMENT 'UTC timestamp when the event occurred on the client/server',
    collector_tstamp    TIMESTAMP_TZ    NOT NULL    COMMENT 'UTC timestamp when the collector received the event',
    loaded_at           TIMESTAMP_TZ    NOT NULL    DEFAULT CURRENT_TIMESTAMP()
                                                    COMMENT 'UTC timestamp when the row was loaded into this table',

    -- Context
    platform_version    VARCHAR(20)     NOT NULL    COMMENT 'GitLab semver running on the tenant instance (e.g., 17.4.2)',
    event_source        VARCHAR(10)     NOT NULL    COMMENT 'Instrumentation side: client or server',

    -- Event-specific properties (semi-structured)
    properties          VARIANT         NULL        COMMENT 'JSON object containing event-specific key-value properties',

    -- Metadata
    sdk_version         VARCHAR(20)     NULL        COMMENT 'Version of the tracking SDK that fired this event',
    ip_hash             VARCHAR(64)     NULL        COMMENT 'SHA-256 hash of the client IP (for geo lookup, not PII)',
    user_agent          VARCHAR(512)    NULL        COMMENT 'Browser/client user agent string',

    -- Constraints
    CONSTRAINT pk_raw_events PRIMARY KEY (event_id)
)
CLUSTER BY (DATE(event_timestamp), tenant_id, event_name)
COMMENT = 'Raw event log for GitLab Dedicated product instrumentation. Source of truth.';


-- =============================================================================
-- 2. FACT TABLE — Transformed Events (Analytics Layer)
-- =============================================================================
-- Description: Cleaned, deduplicated, and enriched event fact table. This is
--              the primary table queried by analysts and BI tools.
-- Grain:      One row per distinct event (deduplicated by event_id).
-- =============================================================================

CREATE TABLE IF NOT EXISTS analytics.fct_dedicated_events (
    -- Surrogate key
    event_key           BIGINT          NOT NULL    IDENTITY(1,1)
                                                    COMMENT 'Auto-incrementing surrogate key',

    -- Natural key
    event_id            VARCHAR(36)     NOT NULL    COMMENT 'Globally unique event identifier (from source)',

    -- Event classification
    event_name          VARCHAR(60)     NOT NULL    COMMENT 'Event name from taxonomy',
    event_category      VARCHAR(30)     NOT NULL    COMMENT 'Logical category (derived if missing from raw)',

    -- Dimension keys (for star schema joins)
    tenant_key          BIGINT          NOT NULL    COMMENT 'FK to dim_tenants.tenant_surrogate_key',
    user_key            BIGINT          NOT NULL    COMMENT 'FK to dim_users.user_surrogate_key',

    -- Natural entity IDs (for convenience / debugging)
    tenant_id           VARCHAR(36)     NOT NULL    COMMENT 'Natural tenant identifier',
    user_id             VARCHAR(36)     NOT NULL    COMMENT 'Natural user identifier',
    session_id          VARCHAR(36)     NULL        COMMENT 'Session identifier',

    -- Time dimensions
    event_timestamp     TIMESTAMP_TZ    NOT NULL    COMMENT 'UTC timestamp of the event',
    event_date          DATE            NOT NULL    COMMENT 'Date extracted from event_timestamp (UTC)',
    event_hour          SMALLINT        NOT NULL    COMMENT 'Hour (0-23) extracted from event_timestamp',
    event_day_of_week   SMALLINT        NOT NULL    COMMENT 'Day of week (1=Mon, 7=Sun)',

    -- Context
    platform_version    VARCHAR(20)     NOT NULL    COMMENT 'GitLab version on the tenant',
    event_source        VARCHAR(10)     NOT NULL    COMMENT 'client or server',

    -- Flattened common properties
    step_name           VARCHAR(60)     NULL        COMMENT 'Onboarding step name (for onboarding events)',
    step_index          SMALLINT        NULL        COMMENT 'Onboarding step index (for ordering)',
    project_id          VARCHAR(36)     NULL        COMMENT 'Project context (if applicable)',
    pipeline_id         VARCHAR(36)     NULL        COMMENT 'Pipeline context (if applicable)',
    pipeline_status     VARCHAR(20)     NULL        COMMENT 'Pipeline result: success, failed, canceled',
    scan_type           VARCHAR(30)     NULL        COMMENT 'Security scan type: sast, dast, dependency, container',
    duration_seconds    INT             NULL        COMMENT 'Duration in seconds (for timed events)',

    -- Full properties (JSON, for ad-hoc analysis)
    properties_json     VARIANT         NULL        COMMENT 'Original JSON properties from raw event',

    -- Pipeline metadata
    loaded_at           TIMESTAMP_TZ    NOT NULL    DEFAULT CURRENT_TIMESTAMP()
                                                    COMMENT 'When this row was created/updated in the fact table',
    dbt_updated_at      TIMESTAMP_TZ    NOT NULL    DEFAULT CURRENT_TIMESTAMP()
                                                    COMMENT 'Last dbt run that touched this row',

    -- Constraints
    CONSTRAINT pk_fct_events PRIMARY KEY (event_key),
    CONSTRAINT uq_fct_event_id UNIQUE (event_id)
)
CLUSTER BY (event_date, tenant_id, event_name)
COMMENT = 'Deduplicated, enriched event fact table for GitLab Dedicated analytics.';


-- =============================================================================
-- 3. DIMENSION TABLE — Tenants (SCD Type 2)
-- =============================================================================

CREATE TABLE IF NOT EXISTS analytics.dim_tenants (
    -- Keys
    tenant_surrogate_key BIGINT         NOT NULL    IDENTITY(1,1)
                                                    COMMENT 'Surrogate key (auto-increment)',
    tenant_id           VARCHAR(36)     NOT NULL    COMMENT 'Natural business key',

    -- Attributes
    tenant_name         VARCHAR(255)    NOT NULL    COMMENT 'Human-readable tenant name',
    region              VARCHAR(20)     NOT NULL    COMMENT 'AWS deployment region (e.g., us-east-1)',
    plan_tier           VARCHAR(30)     NOT NULL    COMMENT 'Subscription tier: premium, ultimate',
    seat_limit          INT             NOT NULL    COMMENT 'Maximum licensed seats',
    seat_count_current  INT             NULL        COMMENT 'Current active seat count',
    sso_enabled         BOOLEAN         NOT NULL    DEFAULT FALSE
                                                    COMMENT 'Whether SAML/SSO is configured',
    provisioning_date   DATE            NOT NULL    COMMENT 'Date the tenant was first provisioned',
    contract_start_date DATE            NULL        COMMENT 'Start of the current subscription contract',
    contract_end_date   DATE            NULL        COMMENT 'End of the current subscription contract',

    -- SCD Type 2 columns
    valid_from          TIMESTAMP_TZ    NOT NULL    COMMENT 'Start of this records validity',
    valid_to            TIMESTAMP_TZ    NULL        COMMENT 'End of validity (NULL = current record)',
    is_current          BOOLEAN         NOT NULL    DEFAULT TRUE
                                                    COMMENT 'TRUE if this is the latest version',

    -- Metadata
    loaded_at           TIMESTAMP_TZ    NOT NULL    DEFAULT CURRENT_TIMESTAMP(),
    dbt_updated_at      TIMESTAMP_TZ    NOT NULL    DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT pk_dim_tenants PRIMARY KEY (tenant_surrogate_key)
)
COMMENT = 'SCD Type 2 dimension table for GitLab Dedicated tenants.';


-- =============================================================================
-- 4. DIMENSION TABLE — Users (SCD Type 2)
-- =============================================================================

CREATE TABLE IF NOT EXISTS analytics.dim_users (
    -- Keys
    user_surrogate_key  BIGINT          NOT NULL    IDENTITY(1,1)
                                                    COMMENT 'Surrogate key (auto-increment)',
    user_id             VARCHAR(36)     NOT NULL    COMMENT 'Natural business key (anonymized)',
    tenant_id           VARCHAR(36)     NOT NULL    COMMENT 'Parent tenant identifier',

    -- Attributes
    role                VARCHAR(30)     NOT NULL    COMMENT 'GitLab role: guest, reporter, developer, maintainer, owner',
    is_active           BOOLEAN         NOT NULL    DEFAULT TRUE
                                                    COMMENT 'Whether the account is currently active',
    invite_date         DATE            NULL        COMMENT 'Date the user was first invited',
    first_login_date    DATE            NULL        COMMENT 'Date of first successful login',
    activation_date     DATE            NULL        COMMENT 'Date the user met activation criteria',
    onboarding_status   VARCHAR(20)     NULL        COMMENT 'not_started, in_progress, completed, abandoned',

    -- SCD Type 2 columns
    valid_from          TIMESTAMP_TZ    NOT NULL,
    valid_to            TIMESTAMP_TZ    NULL,
    is_current          BOOLEAN         NOT NULL    DEFAULT TRUE,

    -- Metadata
    loaded_at           TIMESTAMP_TZ    NOT NULL    DEFAULT CURRENT_TIMESTAMP(),
    dbt_updated_at      TIMESTAMP_TZ    NOT NULL    DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT pk_dim_users PRIMARY KEY (user_surrogate_key)
)
COMMENT = 'SCD Type 2 dimension table for GitLab Dedicated users.';


-- =============================================================================
-- 5. DIMENSION TABLE — Sessions (SCD Type 1)
-- =============================================================================

CREATE TABLE IF NOT EXISTS analytics.dim_sessions (
    session_id              VARCHAR(36)     NOT NULL    COMMENT 'Session identifier',
    user_id                 VARCHAR(36)     NOT NULL    COMMENT 'User who initiated the session',
    tenant_id               VARCHAR(36)     NOT NULL    COMMENT 'Tenant context',

    session_start           TIMESTAMP_TZ    NOT NULL    COMMENT 'Session start timestamp (UTC)',
    session_end             TIMESTAMP_TZ    NULL        COMMENT 'Session end timestamp (NULL if active)',
    session_duration_seconds INT            NULL        COMMENT 'Computed: session_end - session_start',

    page_views              INT             NULL        DEFAULT 0
                                                        COMMENT 'Navigation events in this session',
    events_count            INT             NULL        DEFAULT 0
                                                        COMMENT 'Total events fired in this session',

    device_type             VARCHAR(20)     NULL        COMMENT 'desktop, mobile, tablet, api',
    browser_family          VARCHAR(50)     NULL        COMMENT 'Chrome, Firefox, Safari, API client, etc.',
    os_family               VARCHAR(50)     NULL        COMMENT 'macOS, Windows, Linux, etc.',

    loaded_at               TIMESTAMP_TZ    NOT NULL    DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT pk_dim_sessions PRIMARY KEY (session_id)
)
COMMENT = 'Session dimension table for GitLab Dedicated. SCD Type 1 (overwrite).';


-- =============================================================================
-- 6. dbt MODEL SPECIFICATION (YAML)
-- =============================================================================
-- Below is the dbt schema.yml specification for the fact table, defining
-- column-level documentation and tests.
-- =============================================================================

/*
models:
  - name: fct_dedicated_events
    description: >
      Deduplicated, enriched event fact table for GitLab Dedicated product
      instrumentation. One row per distinct event. Source: raw.dedicated_events.
    columns:
      - name: event_id
        description: Globally unique event identifier (UUID v4)
        tests:
          - unique
          - not_null

      - name: event_name
        description: Event name from the Dedicated taxonomy
        tests:
          - not_null
          - accepted_values:
              values:
                - dedicated_tenant_provisioned
                - dedicated_user_invited
                - dedicated_user_invitation_accepted
                - dedicated_user_first_login
                - dedicated_onboarding_step_completed
                - dedicated_onboarding_completed
                - dedicated_onboarding_abandoned
                - dedicated_user_activated
                - dedicated_user_role_assigned
                - dedicated_project_created
                - dedicated_pipeline_executed
                - dedicated_mr_created
                - dedicated_mr_merged
                - dedicated_security_scan_completed
                - dedicated_nav_section_clicked
                - dedicated_admin_setting_changed
                - dedicated_sso_configured
                - dedicated_instance_upgrade_initiated

      - name: tenant_id
        description: Dedicated tenant instance identifier
        tests:
          - not_null
          - relationships:
              to: ref('dim_tenants')
              field: tenant_id

      - name: user_id
        description: Anonymized user identifier
        tests:
          - not_null
          - relationships:
              to: ref('dim_users')
              field: user_id

      - name: event_timestamp
        description: UTC timestamp of the event occurrence
        tests:
          - not_null

      - name: event_date
        description: Date partition key derived from event_timestamp
        tests:
          - not_null

      - name: platform_version
        description: GitLab semver version on the tenant
        tests:
          - not_null

  - name: dim_tenants
    description: SCD Type 2 dimension for Dedicated tenants
    columns:
      - name: tenant_surrogate_key
        tests:
          - unique
          - not_null
      - name: tenant_id
        tests:
          - not_null

  - name: dim_users
    description: SCD Type 2 dimension for Dedicated users
    columns:
      - name: user_surrogate_key
        tests:
          - unique
          - not_null
      - name: user_id
        tests:
          - not_null
*/
