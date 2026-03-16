# Measurement Strategy — GitLab Dedicated Instrumentation

> **Version:** 1.0  
> **Last Updated:** 2026-03-16  
> **Author:** Product Analytics Team  
> **Audience:** Product Managers, Engineers, Data Analysts, Privacy & Compliance  

---

## 1. Strategic Questions This Instrumentation Answers

The Dedicated instrumentation layer is purpose-built to answer the following business- and product-critical questions:

| # | Question | Decision It Enables |
|---|----------|---------------------|
| 1 | **What percentage of invited users complete onboarding within 7 days?** | Prioritize onboarding UX improvements; justify Growth team resourcing. |
| 2 | **Where do users drop off in the onboarding funnel, and why?** | Target specific friction steps for redesign (see Workstream 3). |
| 3 | **Which Dedicated features have the highest adoption rate within 30 days of provisioning?** | Inform the default configuration and feature promotion strategy. |
| 4 | **How does CI/CD pipeline usage correlate with tenant retention at 6 and 12 months?** | Validate "pipeline activation" as a leading indicator of retention. |
| 5 | **Are Dedicated tenants using security scanning features at the same rate as GitLab.com users?** | Identify feature gaps or discoverability issues unique to the Dedicated experience. |
| 6 | **What is the median time-to-first-value for new Dedicated tenants?** | Shorten provisioning-to-activation time; benchmark against competitive offerings. |
| 7 | **Which admin configuration actions are most common, and are they causing issues?** | Simplify admin workflows; reduce support ticket volume around configuration. |

---

## 2. Product Surfaces in Scope

| Surface | Examples | Priority |
|---------|----------|----------|
| **Onboarding wizard** | Invitation acceptance, SSH key setup, first project, first pipeline | P0 |
| **CI/CD** | Pipeline creation, execution, configuration edits | P0 |
| **Source Code Management** | Merge requests, code reviews, branch management | P1 |
| **Security & Compliance** | SAST/DAST scans, vulnerability dashboards, compliance frameworks | P1 |
| **Tenant Administration** | SSO config, role management, instance settings, upgrades | P0 |
| **Navigation & Search** | Top-nav clicks, global search, help access | P2 |
| **Package & Container Registry** | Package publish, container image push | P2 |

> **Out of scope (v1):** Billing events, Gitaly-level storage metrics, runner fleet telemetry (these will be covered in a Phase 2 instrumentation plan).

---

## 3. How Dedicated Instrumentation Differs from GitLab.com

| Dimension | GitLab.com (Multi-Tenant SaaS) | GitLab Dedicated (Single-Tenant) |
|-----------|-------------------------------|----------------------------------|
| **Data pipeline** | Events flow to GitLab's central Snowflake warehouse via a shared Snowplow pipeline. | Events are collected per-tenant and forwarded to an isolated landing zone before aggregation. |
| **Tenant isolation** | `namespace_id` distinguishes organizations within a shared schema. | `tenant_id` is the primary partition key; each tenant's data is logically (and optionally physically) separated. |
| **Event volume** | High volume (~billions/day across all users). Models are optimized for scale. | Lower volume per instance but higher cardinality per tenant. Models are optimized for depth. |
| **PII handling** | Governed by GitLab's standard privacy policy; pseudonymized at collection. | Must comply with tenant-specific DPAs. Some tenants require data to remain in specific regions. |
| **Schema evolution** | Centralized; schema changes roll out globally. | Must be coordinated with per-tenant upgrade cadences — not all tenants run the same version simultaneously. |
| **Self-service instrumentation** | Engineering teams can add Snowplow events with standard SDK calls. | Dedicated events require a review to ensure tenant isolation guarantees are maintained. Names must use the `dedicated_` prefix. |

---

## 4. Data Residency & Compliance Considerations

### 4.1 Data Residency

- Dedicated tenants may be deployed in **AWS us-east-1, eu-west-1, ap-southeast-1**, or other contracted regions.
- Event data MUST be stored in the **same region** as the tenant deployment unless the tenant's Data Processing Agreement (DPA) explicitly permits cross-region transfer.
- The event collection endpoint (Snowplow collector or custom ingestion API) must be region-local. Cross-region event forwarding is prohibited without DPA approval.

### 4.2 Privacy & PII

- **No raw PII in event payloads.** Emails, names, and IP addresses must be hashed or omitted.
- `user_id` is an opaque, anonymized identifier mapped internally — never the user's email or username.
- Event properties must be reviewed against GitLab's [Internal Data Classification Standard](https://about.gitlab.com/handbook/security/data-classification-standard/) before implementation.

### 4.3 Consent & Control

- Dedicated tenants have the contractual right to **opt out of product telemetry entirely**. The instrumentation SDK must respect this flag at the tenant level.
- When telemetry is disabled, no events are collected — not even anonymized usage pings.
- Tenants must be able to request a **full deletion of their telemetry data** within 30 days of a written request.

### 4.4 Compliance Frameworks

| Framework | Relevance | Instrumentation Impact |
|-----------|-----------|------------------------|
| GDPR | EU-based tenants / EU data subjects | Right to erasure; data minimization; regional storage |
| SOC 2 Type II | All Dedicated tenants | Audit logging of data access; encryption at rest and in transit |
| FedRAMP | US Government tenants | Strict boundary controls; all telemetry must stay within FedRAMP-authorized boundary |
| HIPAA | Healthcare tenants | BAA required; no PHI in event payloads under any circumstance |

---

## 5. Success Metrics for the Instrumentation Program

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Event coverage across P0 surfaces | 100% of P0 surfaces instrumented within 60 days | Tracked in the Tracking Plan register |
| Data freshness | Events available in BI layer within **< 4 hours** of firing | Pipeline monitoring dashboard |
| Data accuracy | **< 0.1%** variance between raw and BI layer (see Workstream 2) | Weekly reconciliation checks |
| Tenant opt-out compliance | 100% — zero telemetry collected when tenant opts out | Automated compliance tests |
| Time to instrument a new event | **< 5 business days** from approved spec to production | Tracked in instrumentation sprint board |
