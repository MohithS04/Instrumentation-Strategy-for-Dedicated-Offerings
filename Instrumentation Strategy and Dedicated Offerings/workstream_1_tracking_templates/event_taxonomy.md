# Event Taxonomy — GitLab Dedicated

> **Version:** 1.0  
> **Last Updated:** 2026-03-16  
> **Owner:** Data Platform Team  

---

## 1. Naming Convention System

All GitLab Dedicated product events follow a strict naming convention to ensure consistency, searchability, and clarity across teams.

### Pattern

```
dedicated_{domain}_{object}_{action}
```

| Segment | Description | Rules |
|---------|-------------|-------|
| `dedicated` | **Prefix.** Identifies the event as originating from the Dedicated product tier. | Always present. Literal string. |
| `{domain}` | **Business domain.** The product surface area. | One of: `user`, `onboarding`, `project`, `pipeline`, `mr`, `security`, `admin`, `nav`, `billing`, `support`, `instance` |
| `{object}` | **Entity acted upon.** The specific object or concept. | Lowercase noun, singular. E.g., `tenant`, `role`, `setting`, `scan`, `ticket` |
| `{action}` | **Verb describing what happened.** | Past tense. E.g., `created`, `completed`, `clicked`, `changed`, `failed`, `abandoned` |

### Rules

1. All segments use `snake_case` — no camelCase or PascalCase.
2. Maximum event name length: **60 characters**.
3. Events MUST start with `dedicated_`.
4. Avoid abbreviations unless universally understood (`mr` for merge request, `sso` for single sign-on).
5. Actions always use **past tense** (e.g., `completed` not `complete`, `created` not `create`).
6. Avoid generic verbs: prefer `provisioned`, `configured`, `merged` over `done`, `processed`, `handled`.

---

## 2. Event Categories

| Category | Description | When to Use |
|----------|-------------|-------------|
| `onboarding` | User first-time experience events | Invitation, account setup, guided wizard steps |
| `feature_adoption` | Feature usage and engagement events | First use of a capability, repeated usage milestones |
| `navigation` | UI navigation and wayfinding events | Section clicks, page views, search interactions |
| `admin` | Tenant administration and configuration | Settings changes, SSO, role management, upgrades |
| `billing` | Subscription and payment events | Plan changes, seat adjustments, invoice actions |
| `support` | Support interaction events | Ticket creation, escalation, resolution |

---

## 3. Event Taxonomy by Lifecycle Stage

### 3.1 User Lifecycle Events

Track the user journey from invitation through activation and ongoing engagement.

| Event Name | Category | Trigger |
|-----------|----------|---------|
| `dedicated_user_invited` | `onboarding` | Tenant admin sends an invitation to a new user |
| `dedicated_user_invitation_accepted` | `onboarding` | Invitee clicks the invitation link and creates an account |
| `dedicated_user_first_login` | `onboarding` | User logs into the Dedicated instance for the first time |
| `dedicated_onboarding_step_completed` | `onboarding` | User completes a discrete onboarding step (parameterized by `step_name`) |
| `dedicated_onboarding_completed` | `onboarding` | User completes all required onboarding steps |
| `dedicated_onboarding_abandoned` | `onboarding` | User exits onboarding without completing all steps |
| `dedicated_user_activated` | `feature_adoption` | User performs their first "value action" (e.g., first commit, first pipeline) |
| `dedicated_user_role_assigned` | `admin` | User's role is changed within the tenant |
| `dedicated_user_deactivated` | `admin` | User account is deactivated by a tenant admin |

### 3.2 Feature Interaction Events

Track engagement with core GitLab capabilities inside the Dedicated environment.

| Event Name | Category | Trigger |
|-----------|----------|---------|
| `dedicated_project_created` | `feature_adoption` | User creates a new project |
| `dedicated_project_archived` | `feature_adoption` | User archives an existing project |
| `dedicated_pipeline_executed` | `feature_adoption` | A CI/CD pipeline completes (success, failure, or canceled) |
| `dedicated_pipeline_config_updated` | `feature_adoption` | User modifies `.gitlab-ci.yml` configuration |
| `dedicated_mr_created` | `feature_adoption` | User opens a new merge request |
| `dedicated_mr_merged` | `feature_adoption` | A merge request is merged |
| `dedicated_mr_review_requested` | `feature_adoption` | User requests a code review on an MR |
| `dedicated_security_scan_completed` | `feature_adoption` | A SAST/DAST/dependency/container scan finishes |
| `dedicated_security_vulnerability_resolved` | `feature_adoption` | A detected vulnerability is marked as resolved |
| `dedicated_issue_created` | `feature_adoption` | User creates a new issue |
| `dedicated_issue_closed` | `feature_adoption` | An issue is closed |
| `dedicated_wiki_page_created` | `feature_adoption` | User creates a wiki page |
| `dedicated_snippet_created` | `feature_adoption` | User creates a code snippet |
| `dedicated_package_published` | `feature_adoption` | A package is published to the Package Registry |

### 3.3 Admin / Operator Events

Track tenant-level administrative actions specific to the Dedicated deployment model.

| Event Name | Category | Trigger |
|-----------|----------|---------|
| `dedicated_tenant_provisioned` | `admin` | A new Dedicated tenant instance is fully provisioned |
| `dedicated_tenant_config_updated` | `admin` | Tenant-level configuration is modified |
| `dedicated_admin_setting_changed` | `admin` | An instance-level admin setting is updated |
| `dedicated_sso_configured` | `admin` | SSO/SAML provider is configured or updated |
| `dedicated_sso_login_succeeded` | `admin` | A user successfully authenticates via SSO |
| `dedicated_sso_login_failed` | `admin` | An SSO authentication attempt fails |
| `dedicated_instance_upgrade_initiated` | `admin` | Tenant admin initiates a version upgrade |
| `dedicated_instance_upgrade_completed` | `admin` | A version upgrade completes (success or failure) |
| `dedicated_backup_triggered` | `admin` | A manual or scheduled backup is initiated |
| `dedicated_backup_restored` | `admin` | A backup restoration is initiated |
| `dedicated_ip_allowlist_updated` | `admin` | IP allowlist for tenant access is modified |
| `dedicated_audit_log_exported` | `admin` | Tenant admin exports the audit log |

### 3.4 Navigation Events

| Event Name | Category | Trigger |
|-----------|----------|---------|
| `dedicated_nav_section_clicked` | `navigation` | User clicks a top-level navigation section |
| `dedicated_nav_search_executed` | `navigation` | User performs a global search |
| `dedicated_nav_help_accessed` | `navigation` | User opens the help/documentation panel |

---

## 4. Property Standards

### 4.1 Required Properties on Every Event

Every Dedicated event payload MUST include these base properties:

| Property | Type | Description |
|----------|------|-------------|
| `event_id` | `string (UUID)` | Globally unique identifier for this event instance |
| `event_name` | `string` | The event name from the taxonomy |
| `tenant_id` | `string` | The Dedicated tenant instance identifier |
| `user_id` | `string` | Anonymized user identifier (not PII) |
| `timestamp` | `datetime (ISO 8601)` | UTC timestamp of when the event occurred |
| `platform_version` | `string (semver)` | GitLab version running on the tenant instance |
| `session_id` | `string (UUID)` | Browser or API session identifier |
| `event_source` | `string` | `client` or `server` — where the event was fired |

### 4.2 Property Naming Rules

- All property names use `snake_case`.
- Boolean properties: prefix with `is_` or `has_` (e.g., `is_first_time`, `has_approval`).
- Count properties: suffix with `_count` (e.g., `approvals_count`, `vulnerabilities_count`).
- Duration properties: suffix with `_seconds` or `_hours` (e.g., `duration_seconds`).
- Identifiers: suffix with `_id` (e.g., `project_id`, `pipeline_id`).
- No raw PII values — use hashed identifiers or anonymized tokens.

---

## 5. Versioning & Deprecation

| Scenario | Process |
|----------|---------|
| **New event** | Add to taxonomy → Review at Instrumentation Meeting → Implement → QA → Ship |
| **Add property** | Treat as a non-breaking change. Document in changelog. Backfill if feasible. |
| **Remove property** | Mark as deprecated for 90 days → then remove. Notify downstream consumers. |
| **Rename event** | Create new event → run both old and new in parallel for 90 days → deprecate old. |
| **Retire event** | Mark `🗑️ Deprecated` → 90-day grace period → remove from SDK. |
