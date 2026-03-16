# Analyst–Engineering Collaboration Checklist

> **Version:** 1.0  
> **Last Updated:** 2026-03-16  
> **Usage:** Complete this checklist for every new or modified event at the weekly Instrumentation Review meeting.  
> **Attendees:** Product Analyst, Data Engineer, Backend Engineer, PM (optional)  

---

## Pre-Meeting Preparation

Before bringing an event to the Instrumentation Review, the requesting team must prepare:

- [ ] Event is documented in the [Tracking Plan Template](../workstream_1_tracking_templates/tracking_plan_template.md)
- [ ] Event name follows the [Event Taxonomy](../workstream_1_tracking_templates/event_taxonomy.md) naming convention
- [ ] All required properties are defined with data types
- [ ] Priority level (P0/P1/P2) is assigned and justified

---

## Instrumentation Review Checklist

### 1. Event Design & Specification

| # | Check | Owner | Status |
|---|-------|-------|--------|
| 1.1 | Does the event name follow the `dedicated_{domain}_{object}_{action}` convention? | Analyst | ☐ |
| 1.2 | Is the event description clear and unambiguous — would a new engineer know exactly when to fire it? | Analyst | ☐ |
| 1.3 | Are all required base properties included? (`event_id`, `tenant_id`, `user_id`, `timestamp`, `platform_version`, `event_source`) | Analyst + Eng | ☐ |
| 1.4 | Are custom properties correctly typed? (string, int, boolean, float, datetime) | Analyst | ☐ |
| 1.5 | Does any property contain or risk containing PII? If yes, is it hashed/anonymized? | Analyst + Privacy | ☐ |
| 1.6 | Is the property count ≤ 15? If more context is needed, is there a linked dimension table? | Analyst | ☐ |

### 2. Instrumentation Side (Client vs. Server)

| # | Check | Owner | Status |
|---|-------|-------|--------|
| 2.1 | Is the event fired on the correct side? (client-side for UI interactions, server-side for backend operations) | Eng | ☐ |
| 2.2 | If client-side: is the SDK correctly initialized for Dedicated tenants? | Eng | ☐ |
| 2.3 | If server-side: is the event fired at the right point in the request lifecycle (after commit, not before)? | Eng | ☐ |
| 2.4 | Is the `event_source` property correctly set to `client` or `server`? | Eng | ☐ |
| 2.5 | For client-side events: is there a debounce/throttle mechanism to prevent double-firing? | Eng | ☐ |

### 3. Data Quality & Integrity

| # | Check | Owner | Status |
|---|-------|-------|--------|
| 3.1 | Are all required properties present and correctly typed in the payload? (verified via test event) | Eng + Data Eng | ☐ |
| 3.2 | Is `event_id` generated as a UUID v4 at the point of firing (not reused or sequential)? | Eng | ☐ |
| 3.3 | Is `timestamp` set to UTC and captured at the moment of event occurrence (not request receipt)? | Eng | ☐ |
| 3.4 | Are there any edge cases where the event could fire with partial or default data? | Eng | ☐ |
| 3.5 | Is the event idempotent — if the same action is retried, will it produce a new `event_id`? | Eng | ☐ |

### 4. Tenant Isolation & Compliance

| # | Check | Owner | Status |
|---|-------|-------|--------|
| 4.1 | Does the event correctly populate `tenant_id` from the request context? | Eng | ☐ |
| 4.2 | Is the event suppressed when the tenant has opted out of telemetry? | Eng | ☐ |
| 4.3 | Does the event respect the tenant's data residency region? (no cross-region event forwarding) | Eng + Infra | ☐ |
| 4.4 | Has the event been reviewed against the Data Classification Standard? | Privacy | ☐ |

### 5. Testing & Staging Validation

| # | Check | Owner | Status |
|---|-------|-------|--------|
| 5.1 | Has the event been tested in a staging/development Dedicated environment? | Eng | ☐ |
| 5.2 | Has a sample event payload been captured and validated against the expected schema? | Eng + Data Eng | ☐ |
| 5.3 | Does the event appear in the raw Snowflake table within the expected latency window (< 4h)? | Data Eng | ☐ |
| 5.4 | Has the event been verified with at least 3 different trigger scenarios (happy path, edge case, error case)? | Eng + QA | ☐ |
| 5.5 | Are there automated tests (unit or integration) covering the event instrumentation code? | Eng | ☐ |

### 6. Backfill & Historical Data

| # | Check | Owner | Status |
|---|-------|-------|--------|
| 6.1 | Is this a new event or a modification of an existing one? | Analyst | ☐ |
| 6.2 | If new: is there historical data that should be backfilled? | Analyst + Data Eng | ☐ |
| 6.3 | If backfill is needed: has a backfill strategy been documented (source, date range, method)? | Data Eng | ☐ |
| 6.4 | If modified: is the old → new transition plan defined (parallel running period, deprecation)? | Analyst + Eng | ☐ |
| 6.5 | Has the backfill query been tested on a small date range before full execution? | Data Eng | ☐ |

### 7. Downstream Readiness (BI Layer)

| # | Check | Owner | Status |
|---|-------|-------|--------|
| 7.1 | Is there a dbt model (or view) ready to consume this event in the analytics layer? | Data Eng | ☐ |
| 7.2 | Are dbt tests defined for the new event? (`not_null`, `unique`, `accepted_values`, `relationships`) | Data Eng | ☐ |
| 7.3 | Has the event been added to the accepted values list in the `fct_dedicated_events` schema test? | Data Eng | ☐ |
| 7.4 | Will the event appear on any existing dashboard? If so, has the dashboard owner been notified? | Analyst | ☐ |
| 7.5 | Has the event been added to the reconciliation check list (Workstream 2) for the next weekly run? | Data Eng | ☐ |

---

## Review Outcome

| Outcome | Action |
|---------|--------|
| ✅ **Approved** | All checklist items pass. Event proceeds to implementation. |
| 🟡 **Approved with conditions** | Minor items remaining (e.g., dbt model in progress). Event can be implemented but must not ship to production until conditions are met. |
| 🔴 **Blocked** | Critical issues identified (PII risk, wrong event side, missing tenant isolation). Must be resolved and re-reviewed. |

### Sign-Off

| Role | Name | Date | Decision |
|------|------|------|----------|
| Product Analyst | | | ☐ Approve ☐ Block |
| Data Engineer | | | ☐ Approve ☐ Block |
| Backend Engineer | | | ☐ Approve ☐ Block |
| Privacy Review (if applicable) | | | ☐ Approve ☐ Block |
