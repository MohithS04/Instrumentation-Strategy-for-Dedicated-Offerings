# Tracking Plan Template — GitLab Dedicated

> **Version:** 1.0  
> **Last Updated:** 2026-03-16  
> **Owner:** Product Analytics Team  

---

## Purpose

This template standardizes how all GitLab Dedicated product events are defined, documented, and tracked through the instrumentation lifecycle. Every event instrumented in the Dedicated tier must have a corresponding entry in this tracking plan before implementation begins.

---

## Tracking Plan Register

| # | Event Name | Event Category | Trigger Description | Properties / Attributes | Owner | Priority | Implementation Status |
|---|-----------|----------------|---------------------|------------------------|-------|----------|-----------------------|
| 1 | `dedicated_tenant_provisioned` | `admin` | Fires when a new Dedicated tenant instance is fully provisioned and available | `tenant_id` (string), `region` (string), `plan_tier` (string), `provisioning_duration_seconds` (int), `timestamp` (datetime) | Dedicated Platform Team | P0 | ✅ Shipped |
| 2 | `dedicated_user_invited` | `onboarding` | Fires when a tenant admin sends an invitation to a new user | `tenant_id` (string), `inviter_user_id` (string), `invitee_email_hash` (string), `role_assigned` (string), `timestamp` (datetime) | Growth Team | P0 | ✅ Shipped |
| 3 | `dedicated_onboarding_step_completed` | `onboarding` | Fires when a user completes a discrete onboarding step (e.g., SSH key, first project, first pipeline) | `tenant_id` (string), `user_id` (string), `step_name` (string), `step_index` (int), `duration_seconds` (int), `timestamp` (datetime) | Growth Team | P0 | 🔄 In Progress |
| 4 | `dedicated_onboarding_abandoned` | `onboarding` | Fires when a user exits the onboarding wizard without completing all steps | `tenant_id` (string), `user_id` (string), `last_step_completed` (string), `steps_remaining` (int), `timestamp` (datetime) | Growth Team | P0 | 🔄 In Progress |
| 5 | `dedicated_project_created` | `feature_adoption` | Fires when a user creates a new project inside a Dedicated tenant | `tenant_id` (string), `user_id` (string), `project_id` (string), `visibility_level` (string), `template_used` (boolean), `timestamp` (datetime) | Verify Team | P1 | 📋 Planned |
| 6 | `dedicated_pipeline_executed` | `feature_adoption` | Fires on completion of a CI/CD pipeline run | `tenant_id` (string), `user_id` (string), `project_id` (string), `pipeline_id` (string), `status` (string: success/failed/canceled), `duration_seconds` (int), `runner_type` (string), `timestamp` (datetime) | Verify Team | P0 | ✅ Shipped |
| 7 | `dedicated_merge_request_created` | `feature_adoption` | Fires when a user opens a new merge request | `tenant_id` (string), `user_id` (string), `project_id` (string), `mr_id` (string), `source_branch` (string), `target_branch` (string), `timestamp` (datetime) | Create Team | P1 | 📋 Planned |
| 8 | `dedicated_merge_request_merged` | `feature_adoption` | Fires when an MR is merged to the target branch | `tenant_id` (string), `user_id` (string), `project_id` (string), `mr_id` (string), `time_to_merge_hours` (float), `approvals_count` (int), `timestamp` (datetime) | Create Team | P1 | 📋 Planned |
| 9 | `dedicated_security_scan_completed` | `feature_adoption` | Fires when a SAST/DAST/dependency scan finishes | `tenant_id` (string), `user_id` (string), `project_id` (string), `scan_type` (string), `vulnerabilities_found` (int), `severity_critical` (int), `timestamp` (datetime) | Secure Team | P1 | 📋 Planned |
| 10 | `dedicated_nav_section_clicked` | `navigation` | Fires when a user clicks a top-level navigation section | `tenant_id` (string), `user_id` (string), `section_name` (string), `previous_section` (string), `timestamp` (datetime) | Foundations Team | P2 | ⏳ Backlog |
| 11 | `dedicated_admin_setting_changed` | `admin` | Fires when a tenant admin modifies an instance-level setting | `tenant_id` (string), `user_id` (string), `setting_category` (string), `setting_name` (string), `old_value_hash` (string), `new_value_hash` (string), `timestamp` (datetime) | Dedicated Platform Team | P1 | 📋 Planned |
| 12 | `dedicated_sso_configured` | `admin` | Fires when SSO/SAML is configured or updated for a tenant | `tenant_id` (string), `user_id` (string), `provider_type` (string), `configuration_action` (string: created/updated/deleted), `timestamp` (datetime) | Dedicated Platform Team | P0 | ✅ Shipped |
| 13 | `dedicated_user_role_assigned` | `admin` | Fires when a user's role is changed within the tenant | `tenant_id` (string), `admin_user_id` (string), `target_user_id` (string), `previous_role` (string), `new_role` (string), `timestamp` (datetime) | Dedicated Platform Team | P1 | 📋 Planned |
| 14 | `dedicated_instance_upgrade_initiated` | `admin` | Fires when a tenant admin initiates a version upgrade | `tenant_id` (string), `user_id` (string), `from_version` (string), `to_version` (string), `upgrade_type` (string: auto/manual), `timestamp` (datetime) | Dedicated Platform Team | P1 | 🔄 In Progress |
| 15 | `dedicated_support_ticket_created` | `feature_adoption` | Fires when a Dedicated tenant user opens a support ticket | `tenant_id` (string), `user_id` (string), `ticket_id` (string), `severity` (string), `category` (string), `timestamp` (datetime) | Support Ops | P2 | ⏳ Backlog |

---

## Column Definitions

| Column | Description |
|--------|-------------|
| **Event Name** | Unique identifier in `snake_case`. Must begin with `dedicated_` prefix. |
| **Event Category** | Logical grouping: `navigation`, `onboarding`, `feature_adoption`, `admin`, `billing`, `support`. |
| **Trigger Description** | Precise description of the user action or system event that fires this event. |
| **Properties / Attributes** | Key-value pairs attached to the event payload, with data types. |
| **Owner** | Engineering or product team responsible for implementation and maintenance. |
| **Priority** | `P0` = Must-have for launch, `P1` = Required within 30 days, `P2` = Nice-to-have / backlog. |
| **Implementation Status** | `⏳ Backlog` → `📋 Planned` → `🔄 In Progress` → `🧪 In QA` → `✅ Shipped` → `🗑️ Deprecated` |

---

## Governance Rules

1. **Review cadence:** All new events must be reviewed at the weekly Instrumentation Review meeting before implementation begins.
2. **Naming approval:** Event names must follow the taxonomy defined in the Event Taxonomy document and be approved by the Data Platform team.
3. **Property limits:** No event should carry more than 15 properties. If more context is needed, use a linked dimension table.
4. **PII policy:** No event property may contain raw PII (email, name, IP). Use hashed or anonymized identifiers only.
5. **Deprecation process:** Events marked `🗑️ Deprecated` must continue firing for 90 days (with a `deprecated` flag) before removal to allow downstream migrations.
