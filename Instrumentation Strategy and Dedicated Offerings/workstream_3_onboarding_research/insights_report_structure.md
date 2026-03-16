# Insights Report Structure — Onboarding Friction Analysis

> **Version:** 1.0  
> **Last Updated:** 2026-03-16  
> **Author:** Product Analytics Team  
> **Audience:** Growth PM, Dedicated Platform Engineering, Customer Success, UX Design  

---

## Report Outline

This document defines the structure for the final Onboarding Friction Analysis report. Each section includes guidance on content, format, and the evidence required.

---

## Section 1: Executive Summary

**Length:** 1 page maximum  
**Purpose:** Give stakeholders the key takeaway in 60 seconds.

### Content

- **The opportunity:** "Reducing onboarding friction can improve end-to-end conversion by ≥ 30%, translating to an estimated **X additional activated users per quarter** across all Dedicated tenants."
- Current end-to-end funnel conversion rate: **X%** (baseline).
- Target end-to-end funnel conversion rate: **≥ X × 1.3** (30% improvement).
- Top 3 friction points identified (one sentence each).
- Recommended investment: engineering effort estimate (e.g., 2 sprints of targeted UX/SDK work).

### Format

| Metric | Current | Target (30% Improvement) |
|--------|---------|--------------------------|
| E2E Funnel Conversion | X% | X × 1.3% |
| Invitation → First Login | X% | — |
| First Login → SSH Key Setup | X% (⚠️ biggest drop-off) | X + Y% |
| Time-to-First-Value (P50) | X hours | X – Z hours |

---

## Section 2: Top 3 Drop-Off Points

**Purpose:** Deep-dive into the three funnel steps with the highest drop-off rates.

### Structure per Drop-Off Point

For each of the top 3, provide:

#### Drop-Off Point #N: [Step Name]

| Attribute | Detail |
|-----------|--------|
| **Funnel Step** | Step X → Step X+1 |
| **Drop-Off Rate** | X% of users (N users out of M) |
| **Median Time-to-Complete** | X minutes (P50) / Y minutes (P90) |
| **Support Ticket Correlation** | X% of users who drop off here file a support ticket within 48 hours |

**Supporting Data:**
- Drop-off rate by segment (role, SSO, tenant size) — presented as a table.
- Time-series trend: has this gotten better or worse over the past 8 weeks?
- Qualitative signal: top 3 support ticket themes from users at this step.

**Example Drop-Off Points** *(to be populated with real data):*

1. **Step 2 → 3: First Login → SSH Key Setup**
   - Hypothesized cause: Non-developer users lack terminal experience.
   - Drop-off rate: ~40%.
   - Users who skip SSH key setup have a 65% lower activation rate.

2. **Step 4 → 5: First Project → First Pipeline**
   - Hypothesized cause: `.gitlab-ci.yml` creation is intimidating for new users.
   - Drop-off rate: ~35%.
   - Median time-to-complete for those who succeed: 12 minutes (P50), 45 minutes (P90).

3. **Step 0 → 1: Invitation → Acceptance**
   - Hypothesized cause: Invitation email has low open rate; no follow-up reminder.
   - Drop-off rate: ~30%.
   - Second invitation attempt (manual) recovers ~15% of non-responses.

---

## Section 3: Behavioral Patterns Observed

**Purpose:** Highlight correlations and predictive patterns that inform intervention design.

### Pattern Template

| Pattern | Evidence | Implication |
|---------|----------|-------------|
| Users who complete SSH key setup are **2x more likely to activate within 30 days** | Activation rate: 45% (SSH complete) vs. 22% (SSH skipped) | SSH key setup is a leading indicator of activation — investing in making it easier has outsized ROI |
| Users on tenants with SSO enabled have **15% lower drop-off at first login** | SSO login conversion: 92% vs. 77% (password-based) | Recommend SSO as a best practice during tenant provisioning |
| Users who create a project from a template activate **1.5x faster** than those who start blank | TTFV P50: 4h (template) vs. 11h (blank) | Default to template-based project creation in the onboarding wizard |
| **Guest** role users have a 60% drop-off at SSH key setup vs. 25% for **Developer** role | Role-stratified funnel analysis | Consider a role-appropriate onboarding track that skips SSH for non-contributors |
| Users who spend **> 10 minutes** on SSH key step and still fail are **3x more likely to file a support ticket** | Time-on-step correlated with ticket creation | Add in-app help trigger after 5 minutes on SSH key step |

---

## Section 4: Recommended Interventions

**Purpose:** Specific, actionable recommendations tied to each friction point.

### Intervention Template

For each recommendation:

| Attribute | Detail |
|-----------|--------|
| **Friction Point** | Step X → Step X+1: [description] |
| **Intervention Type** | [UX change / In-app nudge / Email / Default change / Documentation / Feature] |
| **Description** | Specific change to implement |
| **Expected Impact** | Estimated drop-off reduction (%) and confidence level |
| **Effort** | Engineering effort estimate (T-shirt: S/M/L) |
| **Priority** | Based on impact × effort matrix |

### Example Interventions

| # | Friction Point | Intervention | Type | Expected Impact | Effort | Priority |
|---|---------------|-------------|------|-----------------|--------|----------|
| 1 | SSH Key Setup (Step 2→3) | Add a "Skip for now" option that lets users proceed with HTTPS clone | UX Change | -15% drop-off at this step | M | 🔴 P0 |
| 2 | SSH Key Setup (Step 2→3) | Show an interactive in-app SSH key generation guide (no terminal needed) | Feature | -10% drop-off at this step | L | 🟡 P1 |
| 3 | SSH Key Setup (Step 2→3) | Trigger a contextual help tooltip after 5 minutes of inactivity | In-app Nudge | -5% drop-off at this step | S | 🟡 P1 |
| 4 | First Pipeline (Step 4→5) | Auto-generate a sample `.gitlab-ci.yml` when a user creates a project from template | Default Change | -12% drop-off at this step | S | 🔴 P0 |
| 5 | First Pipeline (Step 4→5) | Add a "Run your first pipeline" guided walkthrough with visual cues | UX Change | -8% drop-off at this step | M | 🟡 P1 |
| 6 | Invitation (Step 0→1) | Send an automated reminder email at +24h and +72h if invitation is not accepted | Email | -10% drop-off at this step | S | 🔴 P0 |
| 7 | Invitation (Step 0→1) | Redesign invitation email with clear value proposition and single CTA | UX Copy Change | -5% drop-off at this step | S | 🟡 P1 |
| 8 | First Login (Step 1→2) | Pre-fill SSO configuration in the registration flow for SSO-enabled tenants | Feature | -5% drop-off at this step | M | 🟢 P2 |

---

## Section 5: Success Measurement Plan

**Purpose:** Define how the impact of each intervention will be measured post-implementation.

### Measurement Framework

| Intervention | Success Metric | Measurement Method | Timeline | Minimum Detectable Effect |
|-------------|---------------|-------------------|----------|---------------------------|
| SSH "Skip for now" option | Drop-off at Step 2→3 | A/B test: 50/50 split, existing vs. skip option | 4 weeks | 10% relative reduction |
| Sample `.gitlab-ci.yml` | Drop-off at Step 4→5 | Before/after comparison (2 weeks pre vs. 2 weeks post) | 2 weeks post-deploy | 8% relative reduction |
| Invitation reminder emails | Acceptance rate (Step 0→1) | A/B test: control (no reminder) vs. treatment (+24h/+72h) | 3 weeks | 7% relative improvement |
| All interventions combined | E2E funnel conversion | Cohort comparison: pre-intervention vs. post-intervention month | 8 weeks post-deploy | 30% relative improvement |

### Guardrail Metrics

Monitor these to ensure interventions don't cause negative side effects:

| Guardrail Metric | Threshold | Why It Matters |
|-----------------|-----------|----------------|
| Support ticket volume | No increase > 10% | Interventions should reduce, not increase, support burden |
| 30-day retention rate | No decrease | Skipping steps shouldn't compromise long-term engagement |
| SSH key adoption (eventual) | Track for 90 days | Users who skip SSH should still be nudged to configure it later |
| Onboarding completion time | No increase > 20% | Adding steps or pop-ups shouldn't slow down power users |

---

## Appendices

### Appendix A: Data Dictionary

Reference the Event Taxonomy from Workstream 1 for all event definitions and property schemas.

### Appendix B: SQL Queries

Reference the Funnel Analysis Template for all SQL used in this analysis.

### Appendix C: Raw Data Tables

Include summary tables exported from the analysis (funnel counts by week, segment breakdowns) as CSV attachments or embedded tables.

### Appendix D: Methodology Notes

- Funnel is **ordered but not strict** — users may complete steps out of order. The funnel counts a step as "reached" if the event fires at any point within the 30-day window, regardless of order.
- Users who are re-invited (duplicate invitations) are counted once using the **earliest** invitation timestamp.
- Activation is defined using a composite trigger: at least one **commit + one pipeline execution + one MR created/merged** within 30 days.
