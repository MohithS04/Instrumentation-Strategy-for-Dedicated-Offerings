"""
Module 1: Synthetic Data Generator
Generates realistic GitLab Dedicated event data for all workstreams.
"""
import uuid
import random
from datetime import datetime, timedelta
from faker import Faker
from config import (
    NUM_TENANTS, NUM_USERS_PER_TENANT, NUM_DAYS, START_DATE,
    REGIONS, PLAN_TIERS, ONBOARDING_STEPS, EVENT_CATALOG
)

fake = Faker()
Faker.seed(42)
random.seed(42)

GITLAB_VERSIONS = ["17.2.0", "17.3.1", "17.4.0", "17.4.2", "17.5.0"]
NAV_SECTIONS = ["projects", "groups", "milestones", "issues", "merge_requests",
                "ci_cd", "security", "packages", "infrastructure", "admin"]
ADMIN_SETTINGS = ["visibility_level", "signup_restrictions", "ci_runner_config",
                  "email_notifications", "two_factor_auth", "repository_storage"]
ROLES = ["guest", "reporter", "developer", "maintainer", "owner"]
SCAN_TYPES = ["sast", "dast", "dependency_scanning", "container_scanning"]
PIPELINE_STATUSES = ["success", "success", "success", "failed", "canceled"]  # weighted


def generate_tenants():
    """Generate tenant metadata."""
    tenants = []
    for i in range(NUM_TENANTS):
        tenant_id = f"tenant_{fake.company().lower().replace(' ', '_').replace(',', '')[:15]}_{i}"
        prov_date = START_DATE - timedelta(days=random.randint(30, 180))
        tenants.append({
            "tenant_id": tenant_id,
            "tenant_name": fake.company(),
            "region": random.choice(REGIONS),
            "plan_tier": random.choice(PLAN_TIERS),
            "seat_limit": random.choice([25, 50, 100, 250, 500]),
            "sso_enabled": random.random() < 0.6,
            "provisioning_date": prov_date.strftime("%Y-%m-%d"),
            "valid_from": prov_date.strftime("%Y-%m-%dT00:00:00Z"),
            "valid_to": None,
            "is_current": True,
        })
    return tenants


def generate_users(tenants):
    """Generate user metadata per tenant."""
    users = []
    for tenant in tenants:
        num_users = random.randint(*NUM_USERS_PER_TENANT)
        for j in range(num_users):
            invite_date = START_DATE + timedelta(days=random.randint(0, 15))
            users.append({
                "user_id": f"usr_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant["tenant_id"],
                "role": random.choice(ROLES),
                "is_active": random.random() < 0.92,
                "invite_date": invite_date.strftime("%Y-%m-%d"),
                "first_login_date": None,
                "activation_date": None,
                "onboarding_status": "not_started",
                "valid_from": invite_date.strftime("%Y-%m-%dT00:00:00Z"),
                "valid_to": None,
                "is_current": True,
            })
    return users


def _random_ts(base_date, offset_hours=(0, 24)):
    """Random timestamp within offset range."""
    offset = timedelta(hours=random.uniform(*offset_hours))
    ts = base_date + offset
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def generate_events(tenants, users):
    """
    Generate realistic event data simulating the full user lifecycle.
    Includes deliberate quality issues for validation testing.
    """
    events = []
    tenant_map = {t["tenant_id"]: t for t in tenants}
    user_groups = {}
    for u in users:
        user_groups.setdefault(u["tenant_id"], []).append(u)

    for tenant in tenants:
        tenant_users = user_groups.get(tenant["tenant_id"], [])
        version = random.choice(GITLAB_VERSIONS)

        # --- Tenant provisioning ---
        events.append(_make_event(
            "dedicated_tenant_provisioned", "admin", tenant["tenant_id"],
            tenant_users[0]["user_id"] if tenant_users else "system",
            datetime.strptime(tenant["provisioning_date"], "%Y-%m-%d"),
            version,
            {"region": tenant["region"], "plan_tier": tenant["plan_tier"],
             "provisioning_duration_seconds": random.randint(120, 900)},
        ))

        # --- SSO configuration (for SSO-enabled tenants) ---
        if tenant["sso_enabled"]:
            events.append(_make_event(
                "dedicated_sso_configured", "admin", tenant["tenant_id"],
                tenant_users[0]["user_id"] if tenant_users else "system",
                datetime.strptime(tenant["provisioning_date"], "%Y-%m-%d") + timedelta(days=1),
                version,
                {"provider_type": "saml", "configuration_action": "created"},
            ))

        # --- User lifecycle per user ---
        for user in tenant_users:
            invite_dt = datetime.strptime(user["invite_date"], "%Y-%m-%d")

            # Step 0: Invitation
            events.append(_make_event(
                "dedicated_user_invited", "onboarding", tenant["tenant_id"],
                user["user_id"], invite_dt, version,
                {"role_assigned": user["role"], "invitee_email_hash": uuid.uuid4().hex[:16]},
            ))

            # Simulate funnel with realistic drop-offs
            # ~70% accept invitation
            if random.random() > 0.70:
                continue
            accept_dt = invite_dt + timedelta(hours=random.uniform(1, 72))
            events.append(_make_event(
                "dedicated_user_invitation_accepted", "onboarding",
                tenant["tenant_id"], user["user_id"], accept_dt, version, {},
            ))
            user["onboarding_status"] = "in_progress"

            # ~85% of accepters do first login
            if random.random() > 0.85:
                continue
            login_dt = accept_dt + timedelta(minutes=random.uniform(5, 120))
            events.append(_make_event(
                "dedicated_user_first_login", "onboarding",
                tenant["tenant_id"], user["user_id"], login_dt, version, {},
            ))
            user["first_login_date"] = login_dt.strftime("%Y-%m-%d")

            # Onboarding steps with drop-off
            current_dt = login_dt
            steps_done = 0
            for idx, step in enumerate(ONBOARDING_STEPS):
                # SSH key is the big drop-off point (~60% pass)
                if step == "ssh_key_setup" and random.random() > 0.58:
                    events.append(_make_event(
                        "dedicated_onboarding_abandoned", "onboarding",
                        tenant["tenant_id"], user["user_id"], current_dt + timedelta(minutes=10),
                        version,
                        {"last_step_completed": ONBOARDING_STEPS[idx - 1] if idx > 0 else "none",
                         "steps_remaining": len(ONBOARDING_STEPS) - idx},
                    ))
                    user["onboarding_status"] = "abandoned"
                    break

                # Pipeline step drop-off (~65% pass)
                if step == "run_first_pipeline" and random.random() > 0.65:
                    events.append(_make_event(
                        "dedicated_onboarding_abandoned", "onboarding",
                        tenant["tenant_id"], user["user_id"], current_dt + timedelta(minutes=15),
                        version,
                        {"last_step_completed": ONBOARDING_STEPS[idx - 1],
                         "steps_remaining": len(ONBOARDING_STEPS) - idx},
                    ))
                    user["onboarding_status"] = "abandoned"
                    break

                step_duration = random.randint(30, 600)
                current_dt = current_dt + timedelta(seconds=step_duration)

                step_event = _make_event(
                    "dedicated_onboarding_step_completed", "onboarding",
                    tenant["tenant_id"], user["user_id"], current_dt, version,
                    {"step_name": step, "step_index": idx, "duration_seconds": step_duration},
                )

                # DELIBERATE DATA QUALITY ISSUE: ~3% of events have null step_name
                if random.random() < 0.03:
                    step_event["properties"]["step_name"] = None

                events.append(step_event)
                steps_done += 1

                # Create project after create_first_project step
                if step == "create_first_project":
                    events.append(_make_event(
                        "dedicated_project_created", "feature_adoption",
                        tenant["tenant_id"], user["user_id"],
                        current_dt + timedelta(seconds=random.randint(5, 60)), version,
                        {"project_id": f"proj_{uuid.uuid4().hex[:8]}",
                         "visibility_level": random.choice(["private", "internal"]),
                         "template_used": random.random() < 0.4},
                    ))

                # Run pipeline after pipeline step
                if step == "run_first_pipeline":
                    events.append(_make_event(
                        "dedicated_pipeline_executed", "feature_adoption",
                        tenant["tenant_id"], user["user_id"],
                        current_dt + timedelta(seconds=random.randint(30, 300)), version,
                        {"pipeline_id": f"pipe_{uuid.uuid4().hex[:8]}",
                         "project_id": f"proj_{uuid.uuid4().hex[:8]}",
                         "status": random.choice(PIPELINE_STATUSES),
                         "duration_seconds": random.randint(15, 600),
                         "runner_type": random.choice(["shared", "specific"])},
                    ))

            # Onboarding completion
            if steps_done == len(ONBOARDING_STEPS):
                events.append(_make_event(
                    "dedicated_onboarding_completed", "onboarding",
                    tenant["tenant_id"], user["user_id"],
                    current_dt + timedelta(minutes=1), version, {},
                ))
                user["onboarding_status"] = "completed"

                # ~75% activate (first value action)
                if random.random() < 0.75:
                    activation_dt = current_dt + timedelta(hours=random.uniform(1, 96))
                    events.append(_make_event(
                        "dedicated_user_activated", "feature_adoption",
                        tenant["tenant_id"], user["user_id"], activation_dt, version, {},
                    ))
                    user["activation_date"] = activation_dt.strftime("%Y-%m-%d")

            # --- Ongoing activity for active users ---
            if user["onboarding_status"] == "completed" and random.random() < 0.7:
                num_days_active = random.randint(5, NUM_DAYS)
                for _ in range(random.randint(3, 30)):
                    day_offset = random.randint(0, num_days_active)
                    activity_dt = current_dt + timedelta(days=day_offset)

                    # Navigation events
                    events.append(_make_event(
                        "dedicated_nav_section_clicked", "navigation",
                        tenant["tenant_id"], user["user_id"], activity_dt, version,
                        {"section_name": random.choice(NAV_SECTIONS)},
                    ))

                    # Feature events
                    if random.random() < 0.6:
                        events.append(_make_event(
                            "dedicated_pipeline_executed", "feature_adoption",
                            tenant["tenant_id"], user["user_id"],
                            activity_dt + timedelta(minutes=random.randint(10, 120)), version,
                            {"pipeline_id": f"pipe_{uuid.uuid4().hex[:8]}",
                             "project_id": f"proj_{uuid.uuid4().hex[:8]}",
                             "status": random.choice(PIPELINE_STATUSES),
                             "duration_seconds": random.randint(15, 600),
                             "runner_type": random.choice(["shared", "specific"])},
                        ))

                    if random.random() < 0.4:
                        events.append(_make_event(
                            "dedicated_mr_created", "feature_adoption",
                            tenant["tenant_id"], user["user_id"],
                            activity_dt + timedelta(minutes=random.randint(30, 240)), version,
                            {"mr_id": f"mr_{uuid.uuid4().hex[:8]}",
                             "project_id": f"proj_{uuid.uuid4().hex[:8]}"},
                        ))

                    if random.random() < 0.2:
                        events.append(_make_event(
                            "dedicated_security_scan_completed", "feature_adoption",
                            tenant["tenant_id"], user["user_id"],
                            activity_dt + timedelta(minutes=random.randint(60, 360)), version,
                            {"scan_type": random.choice(SCAN_TYPES),
                             "vulnerabilities_found": random.randint(0, 25),
                             "severity_critical": random.randint(0, 3)},
                        ))

        # --- Admin events ---
        admin_users = [u for u in tenant_users if u["role"] in ("owner", "maintainer")]
        for _ in range(random.randint(5, 20)):
            admin_user = random.choice(admin_users) if admin_users else tenant_users[0]
            admin_dt = START_DATE + timedelta(days=random.randint(0, NUM_DAYS))
            events.append(_make_event(
                "dedicated_admin_setting_changed", "admin",
                tenant["tenant_id"], admin_user["user_id"], admin_dt, version,
                {"setting_category": "general",
                 "setting_name": random.choice(ADMIN_SETTINGS)},
            ))

    # --- DELIBERATE QUALITY ISSUES for validation testing ---

    # 1. Add ~50 duplicate events (same event_id)
    duplicate_pool = random.sample(events, min(50, len(events)))
    for evt in duplicate_pool:
        dup = evt.copy()
        dup["properties"] = evt["properties"].copy()
        dup["collector_tstamp"] = _random_ts(
            datetime.strptime(evt["event_timestamp"][:10], "%Y-%m-%d"), (0, 1)
        )
        events.append(dup)

    # 2. Add ~30 events with null required fields
    for _ in range(30):
        bad_event = _make_event(
            random.choice(["dedicated_pipeline_executed", "dedicated_nav_section_clicked"]),
            "feature_adoption", random.choice(tenants)["tenant_id"],
            random.choice(users)["user_id"],
            START_DATE + timedelta(days=random.randint(0, NUM_DAYS)),
            random.choice(GITLAB_VERSIONS), {},
        )
        if random.random() < 0.5:
            bad_event["platform_version"] = None
        else:
            bad_event["session_id"] = None
            bad_event["user_id"] = ""  # empty string = missing
        events.append(bad_event)

    random.shuffle(events)
    return events


def _make_event(event_name, category, tenant_id, user_id, timestamp, version, properties):
    """Create a single event dict."""
    if isinstance(timestamp, str):
        ts_str = timestamp
    else:
        ts_str = timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    collector_offset = timedelta(seconds=random.uniform(0.1, 5.0))
    if isinstance(timestamp, str):
        collector_ts = timestamp
    else:
        collector_ts = (timestamp + collector_offset).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    return {
        "event_id": str(uuid.uuid4()),
        "event_name": event_name,
        "event_category": category,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "session_id": f"sess_{uuid.uuid4().hex[:12]}",
        "event_timestamp": ts_str,
        "collector_tstamp": collector_ts,
        "platform_version": version,
        "event_source": random.choice(["client", "server"]),
        "properties": properties,
        "sdk_version": "2.1.4",
    }


if __name__ == "__main__":
    tenants = generate_tenants()
    users = generate_users(tenants)
    events = generate_events(tenants, users)
    print(f"Generated {len(tenants)} tenants, {len(users)} users, {len(events)} events")
