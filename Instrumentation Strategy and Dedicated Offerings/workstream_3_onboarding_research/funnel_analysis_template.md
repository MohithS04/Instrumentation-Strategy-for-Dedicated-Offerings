# Funnel Analysis Template — GitLab Dedicated Onboarding

> **Version:** 1.0  
> **Last Updated:** 2026-03-16  
> **Owner:** Product Analytics Team  

---

## 1. Onboarding Funnel Definition

The onboarding funnel tracks a user's progression from invitation to activation. Each step maps to a specific tracked event from the Event Taxonomy.

### Funnel Steps

| Step # | Step Name | Event Name | Definition | Success Criteria |
|--------|----------|------------|------------|------------------|
| 0 | **Invitation Sent** | `dedicated_user_invited` | Tenant admin sends an invitation | Baseline — 100% |
| 1 | **Invitation Accepted** | `dedicated_user_invitation_accepted` | Invitee clicks the invitation link | User lands on registration page |
| 2 | **First Login** | `dedicated_user_first_login` | User logs in for the first time | Session created on Dedicated instance |
| 3 | **SSH Key Configured** | `dedicated_onboarding_step_completed` (step_name = `ssh_key_setup`) | User adds an SSH or GPG key | Key stored in user profile |
| 4 | **First Project Created** | `dedicated_project_created` | User creates their first project | Project exists in tenant namespace |
| 5 | **First Pipeline Run** | `dedicated_pipeline_executed` | User triggers their first CI/CD pipeline | Pipeline completes (any status) |
| 6 | **Onboarding Completed** | `dedicated_onboarding_completed` | All guided steps marked complete | Onboarding wizard dismissed |
| 7 | **Activated** | `dedicated_user_activated` | User performs first "value action" (commit + pipeline + MR) | Activation criteria met within 30 days |

---

## 2. Drop-Off Rate Formulas

### Per-Step Drop-Off Rate

```
drop_off_rate(step N) = 1 - (users_completing_step_N / users_completing_step_N-1)
```

### Per-Step Conversion Rate

```
conversion_rate(step N) = users_completing_step_N / users_completing_step_N-1
```

### End-to-End Conversion Rate

```
e2e_conversion = users_completing_step_7 / users_at_step_0
```

---

## 3. Benchmark Targets

| Step # | Step Name | Target Conversion Rate | Target Drop-Off Rate | Benchmark Source |
|--------|----------|----------------------|---------------------|------------------|
| 0 → 1 | Invitation → Accepted | ≥ 70% | ≤ 30% | Industry avg for B2B SaaS invitations |
| 1 → 2 | Accepted → First Login | ≥ 85% | ≤ 15% | Internal GitLab.com data (adjusted) |
| 2 → 3 | First Login → SSH Key | ≥ 60% | ≤ 40% | Historical — this is the known high-friction step |
| 3 → 4 | SSH Key → First Project | ≥ 80% | ≤ 20% | Users past SSH setup tend to continue |
| 4 → 5 | First Project → First Pipeline | ≥ 65% | ≤ 35% | Requires `.gitlab-ci.yml` knowledge |
| 5 → 6 | First Pipeline → Onboarding Complete | ≥ 90% | ≤ 10% | Mostly automated at this point |
| 6 → 7 | Onboarding Complete → Activated | ≥ 75% | ≤ 25% | Activation = sustained usage pattern |
| **0 → 7** | **E2E: Invitation → Activated** | **≥ 20%** | — | Combined target; ≥ 26% post-improvement |

---

## 4. Funnel Analysis SQL

```sql
-- Onboarding funnel analysis for GitLab Dedicated
-- Parameters: :start_date, :end_date (invitation date range)

WITH invited AS (
    SELECT DISTINCT user_id, tenant_id, MIN(event_timestamp) AS invited_at
    FROM raw.dedicated_events
    WHERE event_name = 'dedicated_user_invited'
      AND event_timestamp >= :start_date AND event_timestamp < :end_date
    GROUP BY user_id, tenant_id
),

step_completions AS (
    SELECT
        i.user_id,
        i.tenant_id,
        i.invited_at,

        -- Step 1: Invitation Accepted
        MIN(CASE WHEN e.event_name = 'dedicated_user_invitation_accepted'
                 THEN e.event_timestamp END)           AS step_1_at,

        -- Step 2: First Login
        MIN(CASE WHEN e.event_name = 'dedicated_user_first_login'
                 THEN e.event_timestamp END)           AS step_2_at,

        -- Step 3: SSH Key Configured
        MIN(CASE WHEN e.event_name = 'dedicated_onboarding_step_completed'
                  AND e.step_name = 'ssh_key_setup'
                 THEN e.event_timestamp END)           AS step_3_at,

        -- Step 4: First Project Created
        MIN(CASE WHEN e.event_name = 'dedicated_project_created'
                 THEN e.event_timestamp END)           AS step_4_at,

        -- Step 5: First Pipeline Run
        MIN(CASE WHEN e.event_name = 'dedicated_pipeline_executed'
                 THEN e.event_timestamp END)           AS step_5_at,

        -- Step 6: Onboarding Completed
        MIN(CASE WHEN e.event_name = 'dedicated_onboarding_completed'
                 THEN e.event_timestamp END)           AS step_6_at,

        -- Step 7: Activated
        MIN(CASE WHEN e.event_name = 'dedicated_user_activated'
                 THEN e.event_timestamp END)           AS step_7_at

    FROM invited i
    LEFT JOIN raw.dedicated_events e
        ON  e.user_id   = i.user_id
        AND e.tenant_id = i.tenant_id
        AND e.event_timestamp >= i.invited_at
        AND e.event_timestamp <  DATEADD('day', 30, i.invited_at) -- 30-day window
    GROUP BY i.user_id, i.tenant_id, i.invited_at
)

SELECT
    COUNT(*)                                           AS step_0_invited,
    COUNT(step_1_at)                                   AS step_1_accepted,
    COUNT(step_2_at)                                   AS step_2_first_login,
    COUNT(step_3_at)                                   AS step_3_ssh_key,
    COUNT(step_4_at)                                   AS step_4_first_project,
    COUNT(step_5_at)                                   AS step_5_first_pipeline,
    COUNT(step_6_at)                                   AS step_6_onboarding_done,
    COUNT(step_7_at)                                   AS step_7_activated,

    -- Conversion rates
    ROUND(COUNT(step_1_at) * 100.0 / COUNT(*), 1)     AS cvr_0_to_1,
    ROUND(COUNT(step_2_at) * 100.0 / NULLIF(COUNT(step_1_at), 0), 1) AS cvr_1_to_2,
    ROUND(COUNT(step_3_at) * 100.0 / NULLIF(COUNT(step_2_at), 0), 1) AS cvr_2_to_3,
    ROUND(COUNT(step_4_at) * 100.0 / NULLIF(COUNT(step_3_at), 0), 1) AS cvr_3_to_4,
    ROUND(COUNT(step_5_at) * 100.0 / NULLIF(COUNT(step_4_at), 0), 1) AS cvr_4_to_5,
    ROUND(COUNT(step_6_at) * 100.0 / NULLIF(COUNT(step_5_at), 0), 1) AS cvr_5_to_6,
    ROUND(COUNT(step_7_at) * 100.0 / NULLIF(COUNT(step_6_at), 0), 1) AS cvr_6_to_7,
    ROUND(COUNT(step_7_at) * 100.0 / COUNT(*), 1)     AS cvr_e2e

FROM step_completions;
```

---

## 5. Time-to-Complete per Step SQL

```sql
-- Median time-to-complete for each onboarding step
-- Uses the step_completions CTE from the funnel analysis above

SELECT
    'Step 0→1: Invite → Accept'         AS transition,
    APPROX_PERCENTILE(DATEDIFF('minute', invited_at, step_1_at), 0.5) AS median_minutes,
    APPROX_PERCENTILE(DATEDIFF('minute', invited_at, step_1_at), 0.9) AS p90_minutes
FROM step_completions WHERE step_1_at IS NOT NULL

UNION ALL

SELECT
    'Step 1→2: Accept → First Login',
    APPROX_PERCENTILE(DATEDIFF('minute', step_1_at, step_2_at), 0.5),
    APPROX_PERCENTILE(DATEDIFF('minute', step_1_at, step_2_at), 0.9)
FROM step_completions WHERE step_2_at IS NOT NULL

UNION ALL

SELECT
    'Step 2→3: Login → SSH Key',
    APPROX_PERCENTILE(DATEDIFF('minute', step_2_at, step_3_at), 0.5),
    APPROX_PERCENTILE(DATEDIFF('minute', step_2_at, step_3_at), 0.9)
FROM step_completions WHERE step_3_at IS NOT NULL

UNION ALL

SELECT
    'Step 3→4: SSH Key → First Project',
    APPROX_PERCENTILE(DATEDIFF('minute', step_3_at, step_4_at), 0.5),
    APPROX_PERCENTILE(DATEDIFF('minute', step_3_at, step_4_at), 0.9)
FROM step_completions WHERE step_4_at IS NOT NULL

UNION ALL

SELECT
    'Step 4→5: Project → Pipeline',
    APPROX_PERCENTILE(DATEDIFF('minute', step_4_at, step_5_at), 0.5),
    APPROX_PERCENTILE(DATEDIFF('minute', step_4_at, step_5_at), 0.9)
FROM step_completions WHERE step_5_at IS NOT NULL

UNION ALL

SELECT
    'Step 5→6: Pipeline → Onboarded',
    APPROX_PERCENTILE(DATEDIFF('minute', step_5_at, step_6_at), 0.5),
    APPROX_PERCENTILE(DATEDIFF('minute', step_5_at, step_6_at), 0.9)
FROM step_completions WHERE step_6_at IS NOT NULL

UNION ALL

SELECT
    'Step 6→7: Onboarded → Activated',
    APPROX_PERCENTILE(DATEDIFF('hour', step_6_at, step_7_at), 0.5),
    APPROX_PERCENTILE(DATEDIFF('hour', step_6_at, step_7_at), 0.9)
FROM step_completions WHERE step_7_at IS NOT NULL;
```

---

## 6. Segmentation Dimensions

Apply these cuts to the funnel to identify differential friction:

| Segment | Filter | Rationale |
|---------|--------|-----------|
| **User Role** | `role IN ('developer', 'maintainer', 'owner', 'guest')` | Non-developers may struggle with SSH/pipeline steps |
| **SSO Enabled** | `tenant.sso_enabled = TRUE/FALSE` | SSO adds login complexity |
| **Tenant Region** | `tenant.region` | Regional differences in behavior |
| **Tenant Size** | `tenant.seat_count` buckets: 1–20, 21–100, 101–500, 500+ | Large tenants may have different onboarding patterns |
| **Invitation Cohort** | `WEEK(invited_at)` | Track improvement over time |
| **Platform Version** | `platform_version` | Newer versions may have UX improvements |
