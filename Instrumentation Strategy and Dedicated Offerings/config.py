"""
Configuration for GitLab Dedicated Instrumentation Pipeline
"""
import os
from datetime import datetime, timedelta

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "dedicated_events.duckdb")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
REPORTS_DIR = os.path.join(OUTPUT_DIR, "reports")
CHARTS_DIR = os.path.join(OUTPUT_DIR, "charts")

# --- Data Generation ---
NUM_TENANTS = 8
NUM_USERS_PER_TENANT = (15, 80)  # min, max
NUM_DAYS = 60
START_DATE = datetime(2026, 1, 15)
END_DATE = START_DATE + timedelta(days=NUM_DAYS)

# --- Tenant Regions ---
REGIONS = ["us-east-1", "eu-west-1", "ap-southeast-1", "us-west-2"]
PLAN_TIERS = ["premium", "ultimate"]

# --- Event Taxonomy ---
ONBOARDING_STEPS = [
    "account_setup",
    "ssh_key_setup",
    "create_first_project",
    "configure_ci",
    "run_first_pipeline",
    "invite_teammate",
]

EVENT_CATALOG = {
    "onboarding": [
        "dedicated_user_invited",
        "dedicated_user_invitation_accepted",
        "dedicated_user_first_login",
        "dedicated_onboarding_step_completed",
        "dedicated_onboarding_completed",
        "dedicated_onboarding_abandoned",
    ],
    "feature_adoption": [
        "dedicated_project_created",
        "dedicated_pipeline_executed",
        "dedicated_mr_created",
        "dedicated_mr_merged",
        "dedicated_security_scan_completed",
        "dedicated_user_activated",
    ],
    "admin": [
        "dedicated_tenant_provisioned",
        "dedicated_admin_setting_changed",
        "dedicated_sso_configured",
        "dedicated_user_role_assigned",
        "dedicated_instance_upgrade_initiated",
    ],
    "navigation": [
        "dedicated_nav_section_clicked",
        "dedicated_nav_search_executed",
    ],
}

# --- Validation Thresholds ---
RECONCILIATION_PASS_THRESHOLD = 0.1    # ≤ 0.1% variance
RECONCILIATION_WARN_THRESHOLD = 1.0    # ≤ 1.0%
# > 1.0% = FAIL

# --- Onboarding Funnel ---
FUNNEL_STEPS = [
    {"step": 0, "name": "Invitation Sent",       "event": "dedicated_user_invited"},
    {"step": 1, "name": "Invitation Accepted",    "event": "dedicated_user_invitation_accepted"},
    {"step": 2, "name": "First Login",            "event": "dedicated_user_first_login"},
    {"step": 3, "name": "SSH Key Configured",     "event": "dedicated_onboarding_step_completed"},
    {"step": 4, "name": "First Project Created",  "event": "dedicated_project_created"},
    {"step": 5, "name": "First Pipeline Run",     "event": "dedicated_pipeline_executed"},
    {"step": 6, "name": "Onboarding Completed",   "event": "dedicated_onboarding_completed"},
    {"step": 7, "name": "Activated",              "event": "dedicated_user_activated"},
]

FUNNEL_BENCHMARKS = {
    "0→1": 0.70,
    "1→2": 0.85,
    "2→3": 0.60,
    "3→4": 0.80,
    "4→5": 0.65,
    "5→6": 0.90,
    "6→7": 0.75,
}
