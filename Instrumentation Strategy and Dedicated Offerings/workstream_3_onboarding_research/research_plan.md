# Research Plan — Onboarding Friction Analysis for GitLab Dedicated

> **Version:** 1.0  
> **Last Updated:** 2026-03-16  
> **Research Lead:** Product Analytics Team  
> **Stakeholders:** Growth PM, Dedicated Platform Engineering, Customer Success  
> **Timeline:** 4-week sprint (Weeks 1–2: analysis, Weeks 3–4: recommendations + validation)  

---

## 1. Research Objective

Identify where users drop off or struggle during the GitLab Dedicated onboarding flow and produce actionable recommendations that reduce onboarding friction by **≥ 30%** (measured by improvement in end-to-end funnel conversion rate).

---

## 2. Hypotheses

| # | Hypothesis | Rationale |
|---|-----------|-----------|
| H1 | **Users abandon onboarding at the SSH key configuration step.** | SSH key setup requires terminal familiarity — a known barrier for non-developer personas (PMs, designers) invited to Dedicated instances. |
| H2 | **Time-to-complete for the "Create First Project" step exceeds 5 minutes, causing abandonment.** | Users unfamiliar with GitLab's project structure may struggle with template selection and visibility settings. |
| H3 | **Users who skip guided onboarding have a 50% lower 30-day activation rate.** | Without guided steps, users lack context on where to start, reducing feature discovery. |
| H4 | **The invitation-to-first-login conversion rate is below 60%.** | Invitation emails may land in spam, lack urgency, or fail to convey the value of the Dedicated instance. |
| H5 | **Multi-step SSO configuration during first login adds ≥ 3 minutes of friction.** | SAML/SSO flows involve external IdP redirects that can confuse first-time users. |

---

## 3. Metrics to Analyze

### 3.1 Primary Metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| **End-to-end funnel conversion rate** | % of invited users who complete all onboarding steps | Improve by ≥ 30% |
| **Step-level drop-off rate** | % of users who reach step N but do not complete step N+1 | Identify top 3 highest drop-off steps |
| **Time-to-complete per step** | Median seconds between step start and step completion | P50 < 120s per step |
| **Time-to-first-value (TTFV)** | Time from first login to first "value action" (commit, pipeline, MR) | P50 < 48 hours |

### 3.2 Secondary Metrics

| Metric | Definition |
|--------|-----------|
| 7-day activation rate | % of users performing a value action within 7 days of invitation |
| 30-day retention rate | % of activated users returning in days 8–30 |
| Support ticket rate during onboarding | % of users who file a support ticket within 7 days of invitation |
| Onboarding restart rate | % of users who abandon and later return to restart onboarding |

---

## 4. Data Sources

| Source | Description | Key Tables / Data |
|--------|-------------|-------------------|
| **Event Logs** | Raw Snowplow events from the Dedicated SDK | `raw.dedicated_events` — filtered to onboarding events |
| **Transformed Analytics** | dbt-modeled fact tables | `analytics.fct_dedicated_events`, `analytics.dim_users`, `analytics.dim_tenants` |
| **Session Data** | Server-side session logs | `raw.sessions` — session duration, page sequence |
| **Support Tickets** | Zendesk / GitLab Service Desk exports | Tickets tagged `onboarding`, `setup`, `SSH`, `SSO` within 7 days of user invitation |
| **User Metadata** | User profile attributes | `analytics.dim_users` — `role`, `invite_date`, `first_login_date`, `activation_date` |
| **Tenant Metadata** | Tenant configuration | `analytics.dim_tenants` — `region`, `plan_tier`, `sso_enabled`, `provisioning_date` |

---

## 5. Analysis Methods

### 5.1 Funnel Analysis

- Build a 7-step onboarding funnel (see Funnel Analysis Template).
- Calculate conversion and drop-off rates at each step.
- Segment by `tenant_region`, `user_role`, `sso_enabled` to identify differential friction.

### 5.2 Cohort Analysis

- Group users by **invitation week** to detect trends over time (are newer cohorts doing better or worse?).
- Compare cohorts by tenant attributes (e.g., tenants with SSO enabled vs. those without).

### 5.3 Time-Series Comparison

- Compare onboarding metrics **before vs. after** specific product changes (e.g., SDK version updates, UX changes).
- Use interrupted time-series analysis if a clear intervention point exists.

### 5.4 Behavioral Segmentation

- Cluster users by onboarding behavior patterns using the event sequence:
  - **Fast completers:** Finish all steps in < 30 minutes.
  - **Slow completers:** Finish all steps but take > 7 days.
  - **Partial abandoners:** Complete ≥ 3 steps but stop.
  - **Immediate abandoners:** Complete 0–1 steps.
- Profile each segment by role, tenant size, and SSO configuration.

### 5.5 Support Ticket Correlation

- Join support tickets opened within 7 days of invitation to the user's onboarding funnel position.
- Identify which onboarding step most frequently precedes a support ticket.

---

## 6. Deliverable Timeline

| Week | Activity | Output |
|------|----------|--------|
| Week 1 | Data extraction, funnel construction, quality checks | Clean dataset, initial funnel visualization |
| Week 2 | Cohort analysis, behavioral segmentation, support ticket correlation | Analysis notebooks, segment profiles |
| Week 3 | Synthesize findings, identify top 3 friction points, draft recommendations | Insights Report (draft) |
| Week 4 | Stakeholder review, finalize recommendations, define success metrics | Insights Report (final), measurement plan for interventions |

---

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Low event volume for new Dedicated tenants | Insufficient statistical power | Combine data across all tenants; extend analysis window to 90 days |
| Missing `step_name` values (see Workstream 2 discrepancy) | Incomplete funnel construction | Use `step_index` mapping as fallback; escalate SDK fix |
| Confounding variables (tenant size, industry) | Misleading conclusions | Use stratified analysis; control for tenant cohort characteristics |
| Support tickets not tagged to onboarding | Under-counting support friction | Work with Support Ops to improve tagging; use keyword search as supplement |
