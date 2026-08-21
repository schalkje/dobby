#!/usr/bin/env python3
"""
DORA for DevOps — Azure DevOps PBI risk assessment and test evidence.

Single source of truth for the questionnaire values and scores, the 10-104
thresholds, the test catalogue and its minimum profiles, the effective-status
derivation, and the evidence-completeness rules. The skills' prose narrates
this script; it never re-implements the tables.

Subcommands
    catalog           Print questions, values/scores, and the test catalogue (offline).
    score             Compute scores, class, profile, and the final test set from a
                      plan file (offline, no network).
    read              Fetch a work item's DORA state, tags, and revision.
    check             read + recompute the gates; report gaps. Exit 2 when closure
                      is not allowed.
    write-assessment  Persist flow, answers, scores, class, profile, a Status for all
                      twelve tests, and any opt-in/opt-out motivations.
    write-evidence    Persist Evidence/Motivation for the rows where they apply.
    finalize          Recompute the gates and, only when complete, write
                      DoraEvidenceComplete / DoraClosureAllowed. Requires an attestor.

Guardrails enforced in code (not just prose)
    * Legacy Custom.DORA* application/team-cycle fields are never read or written.
    * Unknown/blank answers are rejected -- never silently defaulted to the
      lowest-scoring option.
    * Q4 = yes forces an explicit Q5 = no (a blank Q5 keeps the item incomplete).
    * Evidence is written only for Required/OptedIn rows, Motivation only for
      OptedIn/OptedOut rows, Status for all twelve, nothing else for NotRequired.
    * An OptedOut status is accepted only when the caller marks it as explicitly
      user-requested and supplies a motivation.
    * DoraEvidenceComplete / DoraClosureAllowed are always recomputed from the
      twelve test rows; a stored value (including a stale `true`) is never trusted.

Authentication (tried in order):
    1. AZURE_DEVOPS_EXT_PAT environment variable (PAT)
    2. ADO_TOKEN environment variable (bearer)
    3. `az account get-access-token` (AAD -- requires Azure CLI)
"""

import argparse
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API_VERSION = "7.1"
ADO_RESOURCE_ID = "499b84ac-1321-427f-aa17-267ca6975798"
MAX_RETRIES = 3
INITIAL_BACKOFF = 2  # seconds

CHANGE_TAG = "Change"
BYPASS_TAG = "bypass"  # read only -- bypassing is a human governance decision

# --------------------------------------------------------------------------
# Questionnaire (docs/dora-for-devops.md section 5) -- exact picklist strings.
# --------------------------------------------------------------------------

QUESTIONS = [
    {
        "key": "q1",
        "field": "Custom.DoraQ1SlaRating",
        "scoreField": "Custom.DoraQ1Score",
        "title": "SLA rating of the affected application",
        "note": "Bronze is absent by design -- Bronze routes to the implicit path.",
        "values": {"silver": {"label": "Silver", "score": 10},
                   "gold": {"label": "Gold", "score": 20}},
    },
    {
        "key": "q2",
        "field": "Custom.DoraQ2MitigatingMeasures",
        "scoreField": "Custom.DoraQ2Score",
        "title": "Mitigating measures",
        "note": "The two-hour boundary is marked indicative in the policy.",
        "values": {
            "withinTwoHoursNoDataCorruptionRisk": {
                "label": "Rollback/roll-forward/feature-flag disabling within 2 hours, no data-corruption risk",
                "score": 0},
            "notWithinTwoHoursOrDataCorruptionRisk": {
                "label": "Not within 2 hours, or data-corruption risk", "score": 20},
        },
    },
    {
        "key": "q3",
        "field": "Custom.DoraQ3ChangeImpact",
        "scoreField": "Custom.DoraQ3Score",
        "title": "Change impact",
        "note": "Connecting to a new source system for the first time is the policy's example of 'large'.",
        "values": {
            "contentOnly": {"label": "Content only (text, images, layout, design)", "score": 0},
            "bugfixOrSmallBusinessLogicChange": {"label": "Bugfix or small business-logic change", "score": 5},
            "mediumBusinessLogicChange": {"label": "Medium business-logic change", "score": 10},
            "largeBusinessLogicOrArchitectureChange": {"label": "Large business-logic or architecture change", "score": 15},
        },
    },
    {
        "key": "q4",
        "field": "Custom.DoraQ4NewFunctionality",
        "scoreField": "Custom.DoraQ4Score",
        "title": "New functionality",
        "note": "yes => Q5 is skipped and forced to 'no'.",
        "values": {"no": {"label": "No", "score": 0},
                   "yes": {"label": "Yes", "score": 3}},
    },
    {
        "key": "q5",
        "field": "Custom.DoraQ5IncidentHistory",
        "scoreField": "Custom.DoraQ5Score",
        "title": "Incident history",
        "note": "Only applicable when Q4 = no.",
        "values": {"no": {"label": "No", "score": 0},
                   "some": {"label": "Some", "score": 3},
                   "many": {"label": "Many", "score": 8}},
    },
    {
        "key": "q6",
        "field": "Custom.DoraQ6Familiarity",
        "scoreField": "Custom.DoraQ6Score",
        "title": "Familiarity with the type of change",
        "note": "Pilot feedback flagged this question as unclear -- explain it, do not just present it.",
        "values": {
            "dailyOperationOrFamiliarCode": {"label": "Daily operation / familiar code", "score": 0},
            "unfamiliarProductModuleOrCode": {"label": "Unfamiliar product/module/code", "score": 3},
            "outsideControlThirdPartyOrOtherTeams": {"label": "Outside control / 3rd party / other teams", "score": 8},
        },
    },
    {
        "key": "q7",
        "field": "Custom.DoraQ7AuthImpact",
        "scoreField": "Custom.DoraQ7Score",
        "title": "Authentication and authorization",
        "values": {
            "none": {"label": "No", "score": 0},
            "applicationRolesOrAccessOnly": {"label": "Application roles/access only", "score": 5},
            "clientOrSensitiveDataAccess": {"label": "Client or sensitive data access", "score": 10},
        },
    },
    {
        "key": "q8",
        "field": "Custom.DoraQ8DataImpact",
        "scoreField": "Custom.DoraQ8Score",
        "title": "Data",
        "values": {
            "none": {"label": "No", "score": 0},
            "queryingOrPresentingData": {"label": "Querying or presenting data", "score": 5},
            "updatingNonClientNonSensitiveData": {"label": "Updating non-client/non-sensitive data", "score": 10},
            "updatingClientOrSensitiveData": {"label": "Updating client or sensitive data", "score": 20},
        },
    },
]

QUESTION_BY_KEY = {q["key"]: q for q in QUESTIONS}

# Implemented bounds are 10-104 (Q1 has no zero-scoring answer), not the policy
# document's 0-110. Thresholds are labelled indicative in the policy.
SCORE_MIN, SCORE_MAX = 10, 104
THRESHOLD_LOW, THRESHOLD_MEDIUM = 40, 70

IMPLICIT_CRITERIA = {
    "bronzeSla": "The change concerns a business application with a Bronze SLA, or a component "
                 "not used by any Silver- or Gold-rated business application.",
    "immediateMitigation": "Rollback, roll-forward, or disabling can immediately revert the change "
                           "without permanent damage -- including no already-corrupted database records.",
}

# --------------------------------------------------------------------------
# Test catalogue (docs/dora-for-devops.md section 6).
# Implementation behaviour, which diverges from the policy prose in two places:
# End User Testing is High, and Red Team consultation / Rollback Plan are Optional.
# --------------------------------------------------------------------------

PROFILE_ORDER = {"Low": 1, "Medium": 2, "High": 3}

TESTS = [
    {"key": "unitTests", "suffix": "UnitTests", "label": "Unit Tests",
     "minimumProfile": "Low", "performedBy": "Team (automated)",
     "evidenceHint": "Link to automated test results"},
    {"key": "automatedE2E", "suffix": "AutomatedE2E", "label": "Automated E2E",
     "minimumProfile": "Low", "performedBy": "Team (automated)",
     "evidenceHint": "Link to automated test results"},
    {"key": "smokeTesting", "suffix": "SmokeTesting", "label": "Smoke Testing",
     "minimumProfile": "Low", "performedBy": "PO, delegate, or automated",
     "evidenceHint": "Positive-test confirmation in the PBI, or linked automated tests"},
    {"key": "automatedSecurityTesting", "suffix": "AutomatedSecurityTesting",
     "label": "Automated Security Testing", "minimumProfile": "Low",
     "performedBy": "Security teams (automated, e.g. ORCA)",
     "evidenceHint": "Link to test results"},
    {"key": "functionalAcceptanceTesting", "suffix": "FunctionalAcceptanceTesting",
     "label": "Functional / Acceptance Testing", "minimumProfile": "Medium",
     "performedBy": "PO or delegate",
     "evidenceHint": "Link to child test tasks or a UAT report"},
    {"key": "integrationTesting", "suffix": "IntegrationTesting", "label": "Integration Testing",
     "minimumProfile": "Medium", "performedBy": "Team, PO, delegate, or automated",
     "evidenceHint": "Link to test results"},
    {"key": "regressionTesting", "suffix": "RegressionTesting", "label": "Regression Testing",
     "minimumProfile": "Medium", "performedBy": "Team, PO, delegate, or automated",
     "evidenceHint": "Link to test results"},
    {"key": "endUserTesting", "suffix": "EndUserTesting", "label": "End User Testing",
     "minimumProfile": "High", "performedBy": "End user",
     "evidenceHint": "Link to child test tasks or a UAT report",
     "divergence": "Implementation says High; the policy narrates end-user testing under Medium."},
    {"key": "performanceTesting", "suffix": "PerformanceTesting", "label": "Performance Testing",
     "minimumProfile": "High", "performedBy": "Team",
     "evidenceHint": "Link to test results"},
    {"key": "penetrationTesting", "suffix": "PenetrationTesting",
     "label": "Security Testing (Penetration Testing)", "minimumProfile": "High",
     "performedBy": "Security Red Team",
     "evidenceHint": "Link to results, or report attached to the PBI"},
    {"key": "redTeamConsultation", "suffix": "RedTeamConsultation",
     "label": "Security Testing (Red Team consultation)", "minimumProfile": "Optional",
     "performedBy": "Team + Security Red Team", "evidenceHint": "Summary of the outcome",
     "manualEvidenceOnly": True,
     "divergence": "Implementation says Optional (opt-in only); the policy describes it as a Medium-level test."},
    {"key": "rollbackPlan", "suffix": "RollbackPlan", "label": "Rollback Plan",
     "minimumProfile": "Optional", "performedBy": "Team or PO",
     "evidenceHint": "Plan available before starting the PBI, plus evidence of execution",
     "manualEvidenceOnly": True,
     "divergence": "Implementation says Optional (opt-in only); the policy describes it as a Medium-level test."},
]

TEST_BY_KEY = {t["key"]: t for t in TESTS}
STATUS_VALUES = ("NotRequired", "Required", "OptedIn", "OptedOut")

# --------------------------------------------------------------------------
# Field references.
# --------------------------------------------------------------------------

F_IN_SCOPE = "Custom.DoraInScope"
F_FLOW = "Custom.DoraFlowType"
F_SCORE = "Custom.DoraFinalRiskScore"
F_CLASS = "Custom.DoraFinalRiskClass"
F_PROFILE = "Custom.DoraSuggestedTestProfile"
F_CLOSURE_ALLOWED = "Custom.DoraClosureAllowed"
F_EVIDENCE_COMPLETE = "Custom.DoraEvidenceComplete"

# Optional, not yet shipped by the extension. Written only when --implicit-criterion-field
# is passed, so the assessment comment stays the primary audit artifact until then.
F_IMPLICIT_CRITERION = "Custom.DoraImplicitCriterion"

CORE_FIELDS = [F_IN_SCOPE, F_FLOW, F_SCORE, F_CLASS, F_PROFILE,
               F_CLOSURE_ALLOWED, F_EVIDENCE_COMPLETE]


def test_fields(suffix):
    return (f"Custom.DoraTest{suffix}Status",
            f"Custom.DoraTest{suffix}Evidence",
            f"Custom.DoraTest{suffix}Motivation")


def all_dora_fields():
    fields = list(CORE_FIELDS)
    for q in QUESTIONS:
        fields += [q["field"], q["scoreField"]]
    for t in TESTS:
        fields += list(test_fields(t["suffix"]))
    return fields


# Every field this script is ever allowed to write. The legacy application/team-cycle
# fields (Custom.DORA, Custom.DORArisk, Custom.DORA_4_eyes, ...) are deliberately absent.
WRITABLE_FIELDS = set(all_dora_fields()) | {F_IMPLICIT_CRITERION}


def fail(msg, *extra):
    print(f"ERROR: {msg}", file=sys.stderr)
    for line in extra:
        print(f"  {line}", file=sys.stderr)
    sys.exit(1)


# --------------------------------------------------------------------------
# Derivation logic.
# --------------------------------------------------------------------------

def profile_requires(suggested_profile, minimum_profile):
    """A test is suggested when the PBI's profile is at or above its minimum.
    Optional items are never auto-suggested."""
    if minimum_profile == "Optional":
        return False
    if suggested_profile not in PROFILE_ORDER:
        # Never silently treat an unrecognized profile as "nothing is required":
        # callers must check profile_valid() and block instead.
        return False
    return PROFILE_ORDER[suggested_profile] >= PROFILE_ORDER[minimum_profile]


def profile_valid(profile):
    """The stored profile must be one of the exact implemented values. An empty,
    mis-cased, or localized value would make every test look NotRequired and turn
    an unevidenced PBI green -- so it is treated as a hard blocker, not a default."""
    return profile in PROFILE_ORDER


def effective_status(suggested, status):
    if suggested and status == "OptedOut":
        return "OptedOut"
    if suggested:
        return "Required"
    if status == "OptedIn":
        return "OptedIn"
    return "NotRequired"


def row_requirements(eff):
    return {
        "inFinalSet": eff in ("Required", "OptedIn"),
        "requiresEvidence": eff in ("Required", "OptedIn"),
        "requiresMotivation": eff in ("OptedIn", "OptedOut"),
    }


def compute_score(answers):
    """Return (per_question, total, skipped_q5). Rejects unknown/blank answers."""
    missing, invalid, per_question = [], [], {}

    q4 = (answers.get("q4") or "").strip()
    skip_q5 = q4 == "yes"

    for q in QUESTIONS:
        key = q["key"]
        if key == "q5" and skip_q5:
            # The extension disables the control and forces "no". Write it explicitly --
            # a blank Q5 keeps the item in the incomplete state.
            per_question[key] = {"value": "no", "score": 0, "label": "No",
                                 "applicable": False, "forced": True}
            continue
        value = (answers.get(key) or "").strip()
        if not value or value.lower() in ("unknown", "?"):
            missing.append(key)
            continue
        if value not in q["values"]:
            invalid.append(f"{key}={value!r} (allowed: {', '.join(sorted(q['values']))})")
            continue
        entry = q["values"][value]
        per_question[key] = {"value": value, "score": entry["score"],
                             "label": entry["label"], "applicable": True, "forced": False}

    if invalid:
        fail("invalid questionnaire answer(s).", *invalid)
    if missing:
        fail("unanswered question(s): " + ", ".join(missing),
             "Ask the user. Never default an unknown answer to the lowest-scoring option.")

    total = sum(p["score"] for p in per_question.values() if p["applicable"])
    return per_question, total, skip_q5


def classify(total):
    if total <= THRESHOLD_LOW:
        return "Low"
    if total <= THRESHOLD_MEDIUM:
        return "Medium"
    return "High"


def build_test_set(profile, statuses):
    """statuses: {key: stored status}. Returns the twelve derived rows."""
    rows = []
    for t in TESTS:
        stored = statuses.get(t["key"]) or "NotRequired"
        if stored not in STATUS_VALUES:
            fail(f"invalid status {stored!r} for test {t['key']}",
                 "allowed: " + ", ".join(STATUS_VALUES))
        suggested = profile_requires(profile, t["minimumProfile"])
        eff = effective_status(suggested, stored)
        row = {"key": t["key"], "label": t["label"], "minimumProfile": t["minimumProfile"],
               "performedBy": t["performedBy"], "evidenceHint": t["evidenceHint"],
               "suggested": suggested, "storedStatus": stored, "effectiveStatus": eff,
               "manualEvidenceOnly": bool(t.get("manualEvidenceOnly"))}
        row.update(row_requirements(eff))
        if t.get("divergence"):
            row["divergence"] = t["divergence"]
        rows.append(row)
    return rows


def statuses_from_plan(profile, opt_ins, opt_outs):
    """Refinement writes a Status for every one of the twelve tests."""
    statuses = {}
    notes = []
    for t in TESTS:
        suggested = profile_requires(profile, t["minimumProfile"])
        key = t["key"]
        if key in opt_outs:
            if not suggested:
                notes.append(f"{key}: opt-out of a non-suggested test is a no-op -- resolves to NotRequired")
                statuses[key] = "NotRequired"
            else:
                statuses[key] = "OptedOut"
        elif key in opt_ins:
            if suggested:
                notes.append(f"{key}: already suggested -- opt-in is redundant, status stays Required")
                statuses[key] = "Required"
            else:
                statuses[key] = "OptedIn"
        else:
            statuses[key] = "Required" if suggested else "NotRequired"
    return statuses, notes


def evaluate_completeness(rows, evidence, motivations):
    """Recompute DoraEvidenceComplete from the twelve rows. Never read the stored flag."""
    gaps = []
    for row in rows:
        key = row["key"]
        if row["requiresEvidence"] and not (evidence.get(key) or "").strip():
            gaps.append({"test": key, "missing": "evidence", "effectiveStatus": row["effectiveStatus"],
                         "hint": row["evidenceHint"]})
        if row["requiresMotivation"] and not (motivations.get(key) or "").strip():
            gaps.append({"test": key, "missing": "motivation", "effectiveStatus": row["effectiveStatus"],
                         "hint": "Motivation is required for every opted-in/opted-out test"})
    return (len(gaps) == 0), gaps


# --------------------------------------------------------------------------
# HTTP / auth.
# --------------------------------------------------------------------------

def get_token():
    pat = os.environ.get("AZURE_DEVOPS_EXT_PAT")
    if pat:
        import base64
        return "Basic", base64.b64encode(f":{pat}".encode()).decode()

    token = os.environ.get("ADO_TOKEN")
    if token:
        return "Bearer", token

    try:
        shell = sys.platform == "win32"
        token = subprocess.check_output(
            ["az", "account", "get-access-token",
             "--resource", ADO_RESOURCE_ID,
             "--query", "accessToken", "-o", "tsv"],
            text=True, stderr=subprocess.PIPE, shell=shell
        ).strip()
        if token:
            return "Bearer", token
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    fail("No authentication method available.",
         "Set AZURE_DEVOPS_EXT_PAT (PAT), ADO_TOKEN (Bearer), or run `az login`.")


def build_url(org_url, project, work_item_id, extra=""):
    org = org_url.rstrip("/")
    proj = urllib.parse.quote(project, safe="")
    return f"{org}/{proj}/_apis/wit/workitems/{work_item_id}?api-version={API_VERSION}{extra}"


def do_request(url, method, payload, content_type=None):
    auth_scheme, auth_value = get_token()
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    ctx = ssl.create_default_context()

    for attempt in range(MAX_RETRIES + 1):
        req = urllib.request.Request(url, data=data, method=method)
        if content_type:
            req.add_header("Content-Type", content_type)
        req.add_header("Authorization", f"{auth_scheme} {auth_value}")
        try:
            resp = urllib.request.urlopen(req, context=ctx)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code in (429, 502, 503, 504) and attempt < MAX_RETRIES:
                retry_after = e.headers.get("Retry-After")
                wait = int(retry_after) if retry_after else INITIAL_BACKOFF * (2 ** attempt)
                print(f"  Retrying in {wait}s (HTTP {e.code})...", file=sys.stderr)
                time.sleep(wait)
                continue
            fail(f"HTTP {e.code}", body)


def patch_fields(org, project, work_item_id, updates, dry_run=False):
    """updates: {field_ref: value}. Only whitelisted DORA fields are ever sent."""
    illegal = sorted(set(updates) - WRITABLE_FIELDS)
    if illegal:
        fail("refusing to write non-DORA or legacy field(s): " + ", ".join(illegal))
    ops = [{"op": "add", "path": f"/fields/{ref}", "value": value}
           for ref, value in updates.items()]
    if dry_run:
        return {"dryRun": True, "operations": ops}
    url = build_url(org, project, work_item_id)
    return do_request(url, "PATCH", ops, "application/json-patch+json")


def fetch_work_item(org, project, work_item_id):
    url = build_url(org, project, work_item_id)
    return do_request(url, "GET", None)


def read_state(org, project, work_item_id):
    """Return the structured DORA state of a work item."""
    return state_from_item(fetch_work_item(org, project, work_item_id))


def state_from_item(item):
    """Pure projection of a work-item payload onto the DORA state. Split out from the
    HTTP fetch so the derivation is testable offline."""
    fields = item.get("fields", {})

    tags = [t.strip() for t in (fields.get("System.Tags") or "").split(";") if t.strip()]
    tag_in_scope = any(t.lower() == CHANGE_TAG.lower() for t in tags)
    bypass = any(t.lower() == BYPASS_TAG.lower() for t in tags)

    answers = {q["key"]: (fields.get(q["field"]) or "") for q in QUESTIONS}
    scores = {q["key"]: fields.get(q["scoreField"]) for q in QUESTIONS}

    statuses, evidence, motivations = {}, {}, {}
    for t in TESTS:
        s_ref, e_ref, m_ref = test_fields(t["suffix"])
        statuses[t["key"]] = fields.get(s_ref) or "NotRequired"
        evidence[t["key"]] = fields.get(e_ref) or ""
        motivations[t["key"]] = fields.get(m_ref) or ""

    profile = fields.get(F_PROFILE) or ""
    dora_fields_present = any(ref in fields for ref in all_dora_fields())
    rows = build_test_set(profile, statuses)
    recomputed_complete, gaps = evaluate_completeness(rows, evidence, motivations)

    stored_complete = bool(fields.get(F_EVIDENCE_COMPLETE))
    stored_closure = bool(fields.get(F_CLOSURE_ALLOWED))
    stored_in_scope = bool(fields.get(F_IN_SCOPE))

    flow = fields.get(F_FLOW) or ""
    risk_class = fields.get(F_CLASS) or ""
    assessment_complete = bool(flow and risk_class and profile_valid(profile))

    for row in rows:
        row["evidence"] = evidence[row["key"]]
        row["motivation"] = motivations[row["key"]]

    return {
        "id": item.get("id"),
        "title": fields.get("System.Title", ""),
        "type": fields.get("System.WorkItemType", ""),
        "state": fields.get("System.State", ""),
        "rev": fields.get("System.Rev"),
        "tags": tags,
        "tagInScope": tag_in_scope,
        "bypassTag": bypass,
        "doraFieldsPresent": dora_fields_present,
        "storedInScope": stored_in_scope,
        "scopeMismatch": tag_in_scope != stored_in_scope,
        "flowType": flow,
        "finalRiskScore": fields.get(F_SCORE),
        "finalRiskClass": risk_class,
        "suggestedTestProfile": profile,
        "suggestedTestProfileValid": profile_valid(profile),
        "assessmentComplete": assessment_complete,
        "answers": answers,
        "scores": scores,
        "tests": rows,
        "storedEvidenceComplete": stored_complete,
        "storedClosureAllowed": stored_closure,
        "recomputedEvidenceComplete": recomputed_complete,
        "evidenceCompleteMismatch": stored_complete != recomputed_complete,
        "gaps": gaps,
    }


# --------------------------------------------------------------------------
# Plan handling.
# --------------------------------------------------------------------------

def load_json_file(path, what):
    if not os.path.isfile(path):
        fail(f"{what} file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except json.JSONDecodeError as e:
            fail(f"{what} file is not valid JSON: {path}", str(e))


def resolve_plan(plan):
    """Validate a plan and derive everything downstream of it. Offline."""
    scope = (plan.get("scope") or "in").strip().lower()
    if scope not in ("in", "out"):
        fail("plan.scope must be 'in' or 'out'")

    result = {"scope": scope, "sourceRev": plan.get("sourceRev"),
              "notes": [], "banner": banner_text(plan.get("sourceRev"))}

    if scope == "out":
        reason = (plan.get("outOfScopeReason") or "").strip()
        if not reason:
            fail("an out-of-scope plan must state outOfScopeReason",
                 "Explain why this PBI is not a significant IT change.")
        result.update({"outOfScopeReason": reason, "flow": "", "finalRiskScore": 0,
                       "finalRiskClass": "Low", "suggestedTestProfile": "Low",
                       "closureAllowed": True, "tests": []})
        return result

    flow = (plan.get("flow") or "").strip()
    if flow not in ("Implicit", "Explicit"):
        fail("plan.flow must be 'Implicit' or 'Explicit' for an in-scope PBI")

    opt_ins = list(plan.get("optIns") or [])
    opt_outs = list(plan.get("optOuts") or [])
    motivations = dict(plan.get("motivations") or {})
    for key in opt_ins + opt_outs:
        if key not in TEST_BY_KEY:
            fail(f"unknown test key: {key}", "allowed: " + ", ".join(sorted(TEST_BY_KEY)))
    overlap = sorted(set(opt_ins) & set(opt_outs))
    if overlap:
        fail("a test cannot be both opted in and opted out: " + ", ".join(overlap))

    if flow == "Implicit":
        criterion = (plan.get("implicitCriterion") or "").strip()
        if criterion not in IMPLICIT_CRITERIA:
            fail("an implicit plan must name the knockout criterion that applies",
                 "allowed: " + ", ".join(sorted(IMPLICIT_CRITERIA)))
        if not (plan.get("implicitEvidence") or "").strip():
            fail("an implicit plan must quote the PBI text substantiating the criterion",
                 "The assessment comment is the primary audit artefact for implicit-Low.")
        result.update({
            "flow": "Implicit",
            "implicitCriterion": criterion,
            "implicitCriterionText": IMPLICIT_CRITERIA[criterion],
            "implicitEvidence": plan["implicitEvidence"].strip(),
            "perQuestion": {},
            "finalRiskScore": 10,  # sentinel written by the extension, not a computed sum
            "finalRiskClass": "Low",
            "suggestedTestProfile": "Low",
            "closureAllowed": True,
        })
        result["notes"].append(
            "FinalRiskScore 10 is a sentinel, not a computed sum. The named criterion and its "
            "quoted substantiation must appear in the mandatory assessment comment.")
    else:
        per_question, total, skipped = compute_score(plan.get("answers") or {})
        if not SCORE_MIN <= total <= SCORE_MAX:
            fail(f"computed score {total} is outside the implemented range {SCORE_MIN}-{SCORE_MAX}")
        risk_class = classify(total)
        result.update({
            "flow": "Explicit",
            "perQuestion": per_question,
            "arithmetic": " + ".join(
                f"{k.upper()}:{v['score']}" for k, v in sorted(per_question.items())
                if v["applicable"]) + f" = {total}",
            "q5Skipped": skipped,
            "finalRiskScore": total,
            "finalRiskClass": risk_class,
            "suggestedTestProfile": risk_class,
            "closureAllowed": True,
        })
        if skipped:
            result["notes"].append("Q4 = yes: Q5 is skipped and written explicitly as 'no'.")

    profile = result["suggestedTestProfile"]
    statuses, notes = statuses_from_plan(profile, opt_ins, opt_outs)
    result["notes"].extend(notes)
    rows = build_test_set(profile, statuses)

    missing_motivation = [r["key"] for r in rows
                          if r["requiresMotivation"] and not (motivations.get(r["key"]) or "").strip()]
    if missing_motivation:
        fail("every opted-in/opted-out test needs a motivation: " + ", ".join(missing_motivation))

    for row in rows:
        row["motivation"] = (motivations.get(row["key"]) or "").strip()
    result["tests"] = rows
    result["assumptions"] = list(plan.get("assumptions") or [])
    return result


def _cell(text):
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def render_assessment_report(resolved):
    """The section 11 report format, rendered from the resolved plan."""
    out = ["# DORA for DevOps Assessment", "", resolved["banner"], ""]

    out += ["## Scope decision", ""]
    if resolved["scope"] == "out":
        out += [f"**Decision:** Out of scope — not a significant IT change.", "",
                f"**Reason:** {resolved['outOfScopeReason']}", "",
                "No scoring performed. DORA fields are written to the neutral, "
                "closure-permitting out-of-scope state.", ""]
        return "\n".join(out)

    out += ["**Decision:** In scope — significant IT change (`Change` tag).", ""]

    if resolved["flow"] == "Implicit":
        out += ["## Implicit assessment", "",
                "| Criterion | Result | Evidence |", "|---|---|---|"]
        for key, text in IMPLICIT_CRITERIA.items():
            hit = key == resolved["implicitCriterion"]
            out.append(f"| {_cell(text)} | {'Yes' if hit else 'Not claimed'} | "
                       f"{_cell(resolved['implicitEvidence']) if hit else ''} |")
        out += ["", "**Implicit classification:** Low (`FinalRiskScore = 10`, a sentinel — not a computed sum)",
                "**Explicit assessment required:** No", ""]
    else:
        out += ["## Explicit assessment", "",
                "| Question | Answer (value) | Score | Basis |", "|---|---|---:|---|"]
        assumptions = {a.get("question"): a.get("note", "assumption")
                       for a in resolved.get("assumptions", []) if isinstance(a, dict)}
        for q in QUESTIONS:
            entry = resolved["perQuestion"][q["key"]]
            basis = assumptions.get(q["key"], "")
            if q["key"] in assumptions:
                basis = f"**assumption** — {_cell(basis)}"
            if entry["forced"]:
                basis = "skipped — Q4 = yes forces Q5 = no"
            out.append(f"| {q['key'].upper()} {_cell(q['title'])} | `{entry['value']}` | "
                       f"{entry['score']} | {basis} |")
        out += ["", f"**Arithmetic:** {resolved['arithmetic']}",
                f"**Class:** {resolved['finalRiskClass']}  ·  "
                f"**Suggested test profile:** {resolved['suggestedTestProfile']}",
                f"**Threshold band:** Low {SCORE_MIN}-{THRESHOLD_LOW} · "
                f"Medium {THRESHOLD_LOW + 1}-{THRESHOLD_MEDIUM} · "
                f"High {THRESHOLD_MEDIUM + 1}-{SCORE_MAX} (implemented range, marked indicative in policy)", ""]

    out += ["## Test plan", "",
            "| Test | Suggested | Effective status | Performed by | Evidence required |",
            "|---|---|---|---|---|"]
    for row in resolved["tests"]:
        out.append(f"| {_cell(row['label'])} | {'yes' if row['suggested'] else 'no'} | "
                   f"{row['effectiveStatus']} | {_cell(row['performedBy'])} | "
                   f"{'yes' if row['requiresEvidence'] else 'no'} |")

    deviations = [r for r in resolved["tests"] if r["requiresMotivation"]]
    out += ["", "## Deviations", ""]
    if deviations:
        out += ["| Test | Direction | Motivation |", "|---|---|---|"]
        for row in deviations:
            direction = "opt-out" if row["effectiveStatus"] == "OptedOut" else "opt-in"
            out.append(f"| {_cell(row['label'])} | {direction} | {_cell(row['motivation'])} |")
    else:
        out.append("None.")

    divergences = sorted({r["divergence"] for r in resolved["tests"] if r.get("divergence")})
    if divergences:
        out += ["", "## Policy divergences (implementation wins — raise with the policy owner)", ""]
        out += [f"- {d}" for d in divergences]

    if resolved["notes"]:
        out += ["", "## Notes", ""] + [f"- {n}" for n in resolved["notes"]]

    out += ["", "## Human decision", "",
            "- Reviewed by: · Role: · Date: · Decision:", ""]
    return "\n".join(out)


def render_check_report(state):
    """Evidence assessment table plus blockers, for the closure phase."""
    out = ["# DORA evidence assessment", "", banner_text(state.get("rev")), ""]
    out += [f"**PBI:** #{state['id']} — {_cell(state['title'])}  ·  "
            f"**Revision:** {state['rev']}  ·  **State:** {state['state']}",
            f"**In scope (Change tag):** {state['tagInScope']}  ·  "
            f"**Flow:** {state['flowType'] or '—'}  ·  "
            f"**Class:** {state['finalRiskClass'] or '—'}  ·  "
            f"**Profile:** {state['suggestedTestProfile'] or '—'}", ""]

    out += ["| Test | Effective status | Evidence | Motivation | Gap |", "|---|---|---|---|---|"]
    gap_keys = {(g["test"], g["missing"]) for g in state.get("gaps", [])}
    for row in state["tests"]:
        gaps = [m for (k, m) in gap_keys if k == row["key"]]
        out.append(f"| {_cell(row['label'])} | {row['effectiveStatus']} | "
                   f"{_cell(row.get('evidence')) or '—'} | {_cell(row.get('motivation')) or '—'} | "
                   f"{', '.join(sorted(gaps)) if gaps else '—'} |")

    out += ["", f"**Recomputed EvidenceComplete:** {state['recomputedEvidenceComplete']}  ·  "
                f"**Stored:** {state['storedEvidenceComplete']}"
                f"{'  ⚠ **mismatch — the stored value is not trusted**' if state['evidenceCompleteMismatch'] else ''}", ""]

    blockers = state.get("blockers", [])
    out += ["## Blockers", ""]
    out += ([f"- {b}" for b in blockers] if blockers else ["None — evidence is complete."])
    out += ["", "> A link is not proof that a test passed. Missing evidence is a gap, never a reason to opt out.",
            "> Human attestation is required before the gate flags are written.", ""]
    return "\n".join(out)


def banner_text(source_rev):
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rev = source_rev if source_rev is not None else "unknown"
    return ("> AI-generated DORA assessment draft.\n"
            "> Human review is required.\n"
            "> This output is not an approval or compliance decision.\n"
            f"> Source PBI revision: {rev} - generated {stamp}")


# --------------------------------------------------------------------------
# Commands.
# --------------------------------------------------------------------------

def cmd_catalog(args):
    print(json.dumps({
        "questions": QUESTIONS,
        "thresholds": {"min": SCORE_MIN, "max": SCORE_MAX,
                       "Low": f"{SCORE_MIN}-{THRESHOLD_LOW}",
                       "Medium": f"{THRESHOLD_LOW + 1}-{THRESHOLD_MEDIUM}",
                       "High": f"{THRESHOLD_MEDIUM + 1}-{SCORE_MAX}"},
        "implicitCriteria": IMPLICIT_CRITERIA,
        "tests": TESTS,
        "statusValues": list(STATUS_VALUES),
        "fields": {"core": CORE_FIELDS,
                   "questions": {q["key"]: [q["field"], q["scoreField"]] for q in QUESTIONS},
                   "tests": {t["key"]: list(test_fields(t["suffix"])) for t in TESTS}},
    }, indent=2))


def cmd_score(args):
    resolved = resolve_plan(load_json_file(args.plan, "plan"))
    if args.report:
        print(render_assessment_report(resolved))
    else:
        print(json.dumps(resolved, indent=2))


def cmd_read(args):
    print(json.dumps(read_state(args.org, args.project, args.work_item_id), indent=2))


def cmd_check(args):
    state = read_state(args.org, args.project, args.work_item_id)
    blockers = []

    if not state["tagInScope"]:
        if state["storedInScope"]:
            blockers.append("The 'Change' tag was removed after the assessment -- re-assess before closing.")
        else:
            state["verdict"] = "out-of-scope"
            state["blockers"] = []
            print(render_check_report(state) if args.report else json.dumps(state, indent=2))
            return
    else:
        if not state["storedInScope"]:
            blockers.append("The PBI was assessed out of scope but now carries the 'Change' tag -- "
                            "the earlier verdict is void, re-assessment is required.")
        if not state["assessmentComplete"]:
            if state["flowType"] and state["finalRiskClass"] and not state["suggestedTestProfileValid"]:
                blockers.append(
                    f"SuggestedTestProfile is {state['suggestedTestProfile']!r}, which is not one of "
                    "Low/Medium/High. The final test set cannot be derived from it — an unrecognized "
                    "profile would make every test look NotRequired. Re-assess rather than closing.")
            else:
                blockers.append(
                    "The DORA assessment was never completed (FlowType, FinalRiskClass, or "
                    "SuggestedTestProfile is empty) — route the user back to refinement.")

    if args.assessed_rev is not None and state["rev"] is not None:
        if state["rev"] != args.assessed_rev:
            state["revisionDrift"] = {"assessedRev": args.assessed_rev, "currentRev": state["rev"]}
            blockers.append(
                f"The PBI moved from revision {args.assessed_rev} to {state['rev']} since the assessment. "
                "Compare Tags and Acceptance Criteria: re-assess if either changed; ignore revision bumps "
                "caused by dobby's own field writes.")

    if state["gaps"]:
        for gap in state["gaps"]:
            blockers.append(f"{gap['test']}: missing {gap['missing']} ({gap['effectiveStatus']})")
    if state["evidenceCompleteMismatch"]:
        blockers.append(
            f"Stored DoraEvidenceComplete ({state['storedEvidenceComplete']}) does not match the recomputed "
            f"value ({state['recomputedEvidenceComplete']}). The stored flag is written by a form contribution "
            "that never runs on a REST write -- trust the recomputation, not the stored value.")

    state["blockers"] = blockers
    state["verdict"] = "ready-to-close" if not blockers else "blocked"
    print(render_check_report(state) if args.report else json.dumps(state, indent=2))
    if blockers:
        sys.exit(2)


def cmd_write_assessment(args):
    resolved = resolve_plan(load_json_file(args.plan, "plan"))
    updates = {}

    # Read first: an out-of-scope write is the single most destructive operation here
    # (it clears the whole assessment and permits closure), so it is guarded at least
    # as tightly as an opt-out. A dry run writes nothing, so it skips the read.
    state = None if args.dry_run else read_state(args.org, args.project, args.work_item_id)

    if resolved["scope"] == "out":
        if state and state["tagInScope"]:
            fail("this PBI carries the `Change` tag, so it is in DORA scope.",
                 "Declaring it out of scope while the tag is present would contradict the tag and "
                 "write a closure-permitting state. Resolve the scope question with the user first; "
                 "the tag is the scope signal and must never be removed to dodge an assessment.")
        if state and state["assessmentComplete"] and not args.discard_existing_assessment:
            fail("this PBI already carries a completed assessment "
                 f"(flow {state['flowType']!r}, class {state['finalRiskClass']!r}).",
                 "Writing the out-of-scope state would erase every answer, score, status, evidence "
                 "and motivation on it. Re-run with --discard-existing-assessment only when the user "
                 "explicitly decided the earlier assessment was wrong.")

        # Neutral, closure-permitting state, with every question/score/test field cleared.
        updates[F_IN_SCOPE] = False
        updates[F_FLOW] = ""
        updates[F_SCORE] = 0
        updates[F_CLASS] = "Low"
        updates[F_PROFILE] = "Low"
        updates[F_CLOSURE_ALLOWED] = True
        updates[F_EVIDENCE_COMPLETE] = True
        for q in QUESTIONS:
            updates[q["field"]] = ""
            updates[q["scoreField"]] = 0
        for t in TESTS:
            s_ref, e_ref, m_ref = test_fields(t["suffix"])
            updates[s_ref] = "NotRequired"
            updates[e_ref] = ""
            updates[m_ref] = ""
    else:
        if state and not state["tagInScope"]:
            fail("this PBI does not carry the `Change` tag, which is the DORA scope signal.",
                 "Add the tag first (with the user's agreement) — writing DoraInScope = true while the "
                 "tag is absent leaves the form hidden and the record self-contradictory.")

        updates[F_IN_SCOPE] = True
        updates[F_FLOW] = resolved["flow"]
        updates[F_SCORE] = resolved["finalRiskScore"]
        updates[F_CLASS] = resolved["finalRiskClass"]
        updates[F_PROFILE] = resolved["suggestedTestProfile"]

        # The questionnaire is complete, so the extension's closure gate is satisfied --
        # but no evidence has been registered yet, and any flag left over from an earlier
        # assessment would be a stale `true`. Reset it here; only `finalize` sets it.
        updates[F_CLOSURE_ALLOWED] = True
        updates[F_EVIDENCE_COMPLETE] = False

        if resolved["flow"] == "Implicit":
            for q in QUESTIONS:
                updates[q["field"]] = ""
                updates[q["scoreField"]] = 0
            if args.implicit_criterion_field:
                updates[F_IMPLICIT_CRITERION] = resolved["implicitCriterion"]
        else:
            for q in QUESTIONS:
                entry = resolved["perQuestion"][q["key"]]
                updates[q["field"]] = entry["value"]
                updates[q["scoreField"]] = entry["score"]

        # A Status for every one of the twelve tests, including NotRequired. Evidence and
        # motivation are cleared wherever they no longer apply: a re-assessment that leaves
        # stale evidence on a now-NotRequired/OptedOut row makes an un-run test look performed.
        for row in resolved["tests"]:
            suffix = TEST_BY_KEY[row["key"]]["suffix"]
            s_ref, e_ref, m_ref = test_fields(suffix)
            updates[s_ref] = row["storedStatus"]
            if not row["requiresEvidence"]:
                updates[e_ref] = ""     # evidence itself is registered at closure
            updates[m_ref] = row["motivation"] if row["requiresMotivation"] else ""

    result = patch_fields(args.org, args.project, args.work_item_id, updates, args.dry_run)
    print(json.dumps({
        "workItemId": args.work_item_id,
        "dryRun": bool(args.dry_run),
        "scope": resolved["scope"],
        "flow": resolved.get("flow", ""),
        "finalRiskScore": resolved.get("finalRiskScore"),
        "finalRiskClass": resolved.get("finalRiskClass"),
        "suggestedTestProfile": resolved.get("suggestedTestProfile"),
        "fieldsWritten": sorted(updates),
        "notes": resolved["notes"],
        "banner": resolved["banner"],
        "reminder": "Post the full assessment (with this banner and the source System.Rev) to the PBI "
                    "discussion. For an implicit-Low PBI the comment is the primary audit artefact.",
        "apiResult": result if args.dry_run else {"id": result.get("id"), "rev": result.get("rev")},
    }, indent=2))


def cmd_write_evidence(args):
    payload = load_json_file(args.evidence, "evidence")
    state = read_state(args.org, args.project, args.work_item_id)

    if not state["tagInScope"]:
        fail("this PBI is not in DORA scope (no 'Change' tag) -- there is no evidence to register.")
    if not state["assessmentComplete"]:
        fail("the DORA assessment is not complete (FlowType, FinalRiskClass, or a valid "
             f"SuggestedTestProfile is missing; profile is {state['suggestedTestProfile']!r}) -- "
             "route the user back to refinement before registering evidence.")

    rows = {r["key"]: dict(r) for r in state["tests"]}
    updates, problems, applied_opt_outs = {}, [], []

    for key, entry in payload.items():
        if key not in TEST_BY_KEY:
            problems.append(f"unknown test key: {key}")
            continue
        if not isinstance(entry, dict):
            problems.append(f"{key}: entry must be an object with 'evidence' and/or 'motivation'")
            continue

        new_status = (entry.get("status") or "").strip()
        if new_status:
            if new_status != "OptedOut":
                problems.append(f"{key}: only an OptedOut status may be set here; every other status "
                                "change belongs to the refinement assessment")
                continue
            if not entry.get("userRequestedOptOut"):
                problems.append(f"{key}: an OptedOut status is accepted only when the user stated it "
                                "explicitly (set userRequestedOptOut: true). Missing evidence is a gap, "
                                "never a reason to opt out")
                continue
            if not (entry.get("motivation") or "").strip():
                problems.append(f"{key}: an opt-out needs a motivation")
                continue
            row = rows[key]
            if not row["suggested"]:
                problems.append(f"{key}: opting out of a non-suggested test is a no-op")
                continue
            row["storedStatus"] = "OptedOut"
            row["effectiveStatus"] = "OptedOut"
            row.update(row_requirements("OptedOut"))
            suffix = TEST_BY_KEY[key]["suffix"]
            updates[test_fields(suffix)[0]] = "OptedOut"
            # An opted-out test was not performed: any evidence carried over from when the
            # row was Required must go, or the record would still show a passing test.
            updates[test_fields(suffix)[1]] = ""
            row["evidence"] = ""
            applied_opt_outs.append(key)

        row = rows[key]
        suffix = TEST_BY_KEY[key]["suffix"]
        s_ref, e_ref, m_ref = test_fields(suffix)

        ev = (entry.get("evidence") or "").strip()
        if ev:
            if not row["requiresEvidence"]:
                problems.append(f"{key}: evidence is not applicable to a {row['effectiveStatus']} row -- "
                                "writing it would make an un-run test look performed")
            else:
                updates[e_ref] = ev
                row["evidence"] = ev

        mot = (entry.get("motivation") or "").strip()
        if mot:
            if not row["requiresMotivation"]:
                problems.append(f"{key}: motivation is not applicable to a {row['effectiveStatus']} row")
            else:
                updates[m_ref] = mot
                row["motivation"] = mot

    if problems:
        fail("evidence payload rejected.", *problems)

    result = patch_fields(args.org, args.project, args.work_item_id, updates, args.dry_run) if updates else None

    row_list = list(rows.values())
    complete, gaps = evaluate_completeness(
        row_list,
        {k: r.get("evidence", "") for k, r in rows.items()},
        {k: r.get("motivation", "") for k, r in rows.items()})

    print(json.dumps({
        "workItemId": args.work_item_id,
        "dryRun": bool(args.dry_run),
        "fieldsWritten": sorted(updates),
        "optOutsApplied": applied_opt_outs,
        "recomputedEvidenceComplete": complete,
        "gaps": gaps,
        "reminder": "A link is not proof that a test passed. Only report a test as passed when the "
                    "referenced content says so or the user confirms it.",
        "apiResult": result if args.dry_run else ({"id": result.get("id"), "rev": result.get("rev")} if result else None),
    }, indent=2))
    if gaps:
        sys.exit(2)


def cmd_finalize(args):
    attestor = (args.attested_by or "").strip()
    if not attestor:
        fail("--attested-by is required: a human must attest to the evidence before the gates are written.")

    state = read_state(args.org, args.project, args.work_item_id)
    if not state["tagInScope"]:
        fail("this PBI is not in DORA scope -- nothing to finalize.")
    if not state["assessmentComplete"]:
        fail("the DORA assessment is not complete (FlowType, FinalRiskClass, or a valid "
             f"SuggestedTestProfile is missing; profile is {state['suggestedTestProfile']!r}) -- "
             "route the user back to refinement.")

    if not state["recomputedEvidenceComplete"]:
        print(json.dumps({
            "workItemId": args.work_item_id,
            "written": False,
            "recomputedEvidenceComplete": False,
            "storedEvidenceComplete": state["storedEvidenceComplete"],
            "gaps": state["gaps"],
            "message": "Evidence is incomplete -- no flags written and no state transition. Report the "
                       "named test keys as gaps. Opting out to clear a gap is not an option.",
        }, indent=2))
        sys.exit(2)

    updates = {F_EVIDENCE_COMPLETE: True, F_CLOSURE_ALLOWED: True}
    result = patch_fields(args.org, args.project, args.work_item_id, updates, args.dry_run)

    attested_at = args.attested_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(json.dumps({
        "workItemId": args.work_item_id,
        "dryRun": bool(args.dry_run),
        "written": not args.dry_run,
        "fieldsWritten": sorted(updates),
        "attestedBy": attestor,
        "attestedAt": attested_at,
        "sourceRev": state["rev"],
        "nextStep": "Re-read the work item and verify both flags before setting System.State = Done. "
                    "Never write ClosureAllowed and transition in a single action.",
        "apiResult": result if args.dry_run else {"id": result.get("id"), "rev": result.get("rev")},
    }, indent=2))


# --------------------------------------------------------------------------

def add_ado_args(p):
    p.add_argument("--work-item-id", required=True, type=int, help="Work item ID")
    p.add_argument("--org", required=True, help="Azure DevOps organization URL")
    p.add_argument("--project", required=True, help="Azure DevOps project name")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="DORA for DevOps risk assessment and test evidence for Azure DevOps PBIs.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("catalog", help="Print the questionnaire, thresholds, and test catalogue (offline)")
    p.set_defaults(func=cmd_catalog)

    p = sub.add_parser("score", help="Resolve a plan file into scores, class, profile, and test set (offline)")
    p.add_argument("--plan", required=True, help="Path to the assessment plan JSON")
    p.add_argument("--report", action="store_true", help="Render the Markdown assessment report instead of JSON")
    p.set_defaults(func=cmd_score)

    p = sub.add_parser("read", help="Read a work item's DORA state")
    add_ado_args(p)
    p.set_defaults(func=cmd_read)

    p = sub.add_parser("check", help="Recompute the gates and report blockers (exit 2 when blocked)")
    add_ado_args(p)
    p.add_argument("--assessed-rev", type=int, default=None,
                   help="System.Rev recorded when the assessment was made, to detect drift")
    p.add_argument("--report", action="store_true", help="Render the Markdown evidence report instead of JSON")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("write-assessment", help="Persist the refinement assessment")
    add_ado_args(p)
    p.add_argument("--plan", required=True, help="Path to the assessment plan JSON")
    p.add_argument("--implicit-criterion-field", action="store_true",
                   help="Also write Custom.DoraImplicitCriterion (only if the extension ships that field)")
    p.add_argument("--discard-existing-assessment", action="store_true",
                   help="Allow an out-of-scope write to erase an existing completed assessment "
                        "(only when the user explicitly decided it was wrong)")
    p.add_argument("--dry-run", action="store_true", help="Print the patch operations without sending them")
    p.set_defaults(func=cmd_write_assessment)

    p = sub.add_parser("write-evidence", help="Persist Evidence/Motivation where they apply")
    add_ado_args(p)
    p.add_argument("--evidence", required=True, help="Path to the evidence JSON")
    p.add_argument("--dry-run", action="store_true", help="Print the patch operations without sending them")
    p.set_defaults(func=cmd_write_evidence)

    p = sub.add_parser("finalize", help="Write the gate flags after human attestation")
    add_ado_args(p)
    p.add_argument("--attested-by", required=True, help="Name/alias of the human who attested to the evidence")
    p.add_argument("--attested-at", default=None, help="ISO-8601 timestamp of the attestation")
    p.add_argument("--dry-run", action="store_true", help="Print the patch operations without sending them")
    p.set_defaults(func=cmd_finalize)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
