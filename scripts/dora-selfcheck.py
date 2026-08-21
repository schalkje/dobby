"""Offline self-check for skills/_lib/azdo-dora.py — scoring, derivation, and guardrails.

Not part of the shipped skill set; run manually:  python scripts/dora-selfcheck.py
"""
import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "azdo_dora", Path(__file__).resolve().parent.parent / "skills" / "_lib" / "azdo-dora.py")
dora = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dora)

failures = []


def check(label, actual, expected):
    if actual != expected:
        failures.append(f"{label}: expected {expected!r}, got {actual!r}")


def resolve(plan):
    return dora.resolve_plan(plan)


def expect_fail(label, plan, needle):
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            old, sys.stderr = sys.stderr, buf
            try:
                resolve(plan)
            finally:
                sys.stderr = old
    except SystemExit as e:
        if e.code != 1:
            failures.append(f"{label}: exited {e.code}, expected 1")
        if needle.lower() not in buf.getvalue().lower():
            failures.append(f"{label}: message {buf.getvalue()!r} missing {needle!r}")
        return
    failures.append(f"{label}: expected a rejection, got none")


# --- scoring boundaries -----------------------------------------------------
minimal = {"q1": "silver", "q2": "withinTwoHoursNoDataCorruptionRisk", "q3": "contentOnly",
           "q4": "no", "q5": "no", "q6": "dailyOperationOrFamiliarCode", "q7": "none", "q8": "none"}
per_q, total, skipped = dora.compute_score(minimal)
check("minimum reachable score", total, 10)
check("minimum class", dora.classify(total), "Low")
check("q5 not skipped", skipped, False)

maximal = {"q1": "gold", "q2": "notWithinTwoHoursOrDataCorruptionRisk",
           "q3": "largeBusinessLogicOrArchitectureChange", "q4": "no", "q5": "many",
           "q6": "outsideControlThirdPartyOrOtherTeams", "q7": "clientOrSensitiveDataAccess",
           "q8": "updatingClientOrSensitiveData"}
_, total_max, _ = dora.compute_score(maximal)
check("maximum reachable score", total_max, 101)
check("maximum class", dora.classify(total_max), "High")
check("threshold 40 -> Low", dora.classify(40), "Low")
check("threshold 41 -> Medium", dora.classify(41), "Medium")
check("threshold 70 -> Medium", dora.classify(70), "Medium")
check("threshold 71 -> High", dora.classify(71), "High")

# Q4 = yes forces an explicit Q5 = no, and Q5 contributes 0.
q4yes = dict(minimal, q4="yes", q5="many")
per_q, total, skipped = dora.compute_score(q4yes)
check("q4=yes skips q5", skipped, True)
check("q5 forced to no", per_q["q5"]["value"], "no")
check("q5 excluded from total", total, 13)

# --- profile / effective status --------------------------------------------
check("Optional never suggested", dora.profile_requires("High", "Optional"), False)
check("High covers Medium", dora.profile_requires("High", "Medium"), True)
check("Low does not cover Medium", dora.profile_requires("Low", "Medium"), False)
check("profile_valid accepts High", dora.profile_valid("High"), True)
check("profile_valid rejects mis-cased", dora.profile_valid("high"), False)
check("profile_valid rejects empty", dora.profile_valid(""), False)
check("profile_valid rejects unknown", dora.profile_valid("Critical"), False)
# An unrecognized profile must never be silently read as "nothing is required": the value
# is a hard blocker (assessmentComplete is false), not a default.
check("unknown profile suggests nothing", dora.profile_requires("high", "Low"), False)
check("suggested+OptedOut", dora.effective_status(True, "OptedOut"), "OptedOut")
check("suggested default", dora.effective_status(True, "NotRequired"), "Required")
check("unsuggested+OptedIn", dora.effective_status(False, "OptedIn"), "OptedIn")
check("unsuggested+OptedOut is a no-op", dora.effective_status(False, "OptedOut"), "NotRequired")

reqs = dora.row_requirements("OptedOut")
check("OptedOut needs no evidence", reqs["requiresEvidence"], False)
check("OptedOut needs motivation", reqs["requiresMotivation"], True)
reqs = dora.row_requirements("Required")
check("Required needs evidence", reqs["requiresEvidence"], True)
check("Required needs no motivation", reqs["requiresMotivation"], False)

# --- completeness -----------------------------------------------------------
rows = dora.build_test_set("Low", {t["key"]: "Required" if t["minimumProfile"] == "Low" else "NotRequired"
                                   for t in dora.TESTS})
complete, gaps = dora.evaluate_completeness(rows, {}, {})
check("empty evidence is incomplete", complete, False)
check("low profile gap count", len(gaps), 4)
ev = {r["key"]: "https://build/123" for r in rows if r["requiresEvidence"]}
complete, gaps = dora.evaluate_completeness(rows, ev, {})
check("filled evidence is complete", complete, True)

# --- plan guardrails --------------------------------------------------------
expect_fail("unknown answer rejected",
            {"scope": "in", "flow": "Explicit", "answers": dict(minimal, q3="")},
            "unanswered")
expect_fail("invalid picklist rejected",
            {"scope": "in", "flow": "Explicit", "answers": dict(minimal, q1="bronze")},
            "invalid questionnaire")
expect_fail("implicit needs a criterion",
            {"scope": "in", "flow": "Implicit"},
            "knockout criterion")
expect_fail("implicit needs quoted substantiation",
            {"scope": "in", "flow": "Implicit", "implicitCriterion": "bronzeSla"},
            "quote the pbi text")
expect_fail("out-of-scope needs a reason", {"scope": "out"}, "outofscopereason")
expect_fail("opt-out needs a motivation",
            {"scope": "in", "flow": "Explicit", "answers": minimal, "optOuts": ["unitTests"]},
            "needs a motivation")
expect_fail("opt-in needs a motivation",
            {"scope": "in", "flow": "Explicit", "answers": minimal, "optIns": ["rollbackPlan"]},
            "needs a motivation")
expect_fail("unknown test key rejected",
            {"scope": "in", "flow": "Explicit", "answers": minimal, "optIns": ["chaosTesting"]},
            "unknown test key")

implicit = resolve({"scope": "in", "flow": "Implicit", "implicitCriterion": "bronzeSla",
                    "implicitEvidence": "\"The reporting portal carries a Bronze SLA.\"", "sourceRev": 7})
check("implicit sentinel score", implicit["finalRiskScore"], 10)
check("implicit class", implicit["finalRiskClass"], "Low")
check("implicit profile", implicit["suggestedTestProfile"], "Low")
check("implicit statuses written for all twelve", len(implicit["tests"]), 12)
check("banner carries the rev", "Source PBI revision: 7" in implicit["banner"], True)

out_of_scope = resolve({"scope": "out", "outOfScopeReason": "Documentation-only change."})
check("out-of-scope writes no tests", out_of_scope["tests"], [])

# --- state projection -------------------------------------------------------
def item(**overrides):
    fields = {"System.Tags": "Change", dora.F_FLOW: "Explicit", dora.F_CLASS: "High",
              dora.F_PROFILE: "High", dora.F_IN_SCOPE: True}
    fields.update(overrides)
    return {"id": 1, "fields": fields}

state = dora.state_from_item(item())
check("complete assessment recognized", state["assessmentComplete"], True)
check("high profile requires tests", any(r["requiresEvidence"] for r in state["tests"]), True)

# A profile the implementation does not know must not degrade into "nothing required".
state = dora.state_from_item(item(**{dora.F_PROFILE: "high"}))
check("mis-cased profile is invalid", state["suggestedTestProfileValid"], False)
check("mis-cased profile blocks completion", state["assessmentComplete"], False)
state = dora.state_from_item(item(**{dora.F_PROFILE: ""}))
check("empty profile blocks completion", state["assessmentComplete"], False)

# A stored `true` gate that the rows do not support must surface as a mismatch.
state = dora.state_from_item(item(**{dora.F_EVIDENCE_COMPLETE: True}))
check("stale green gate detected", state["evidenceCompleteMismatch"], True)
check("recomputed gate wins", state["recomputedEvidenceComplete"], False)

state = dora.state_from_item(item(**{"System.Tags": "", dora.F_IN_SCOPE: True}))
check("scope mismatch detected", state["scopeMismatch"], True)

# --- writable-field whitelist ----------------------------------------------
legacy = ["Custom.DORA", "Custom.DORArisk", "Custom.DORA_4_eyes", "Custom.DORA_pentest",
          "Custom.DORA_no_risk", "Custom.DORA_automated_test"]
for field in legacy:
    check(f"legacy field {field} not writable", field in dora.WRITABLE_FIELDS, False)
check("twelve test rows", len(dora.TESTS), 12)
check("eight questions", len(dora.QUESTIONS), 8)

# --- report rendering -------------------------------------------------------
report = dora.render_assessment_report(resolve(
    {"scope": "in", "flow": "Explicit", "answers": maximal, "sourceRev": 3,
     "assumptions": [{"question": "q6", "note": "No familiarity signal in the PBI."}]}))
check("report has banner", "AI-generated DORA assessment draft" in report, True)
check("report marks assumptions", "**assumption**" in report, True)
check("report shows arithmetic", "= 101" in report, True)

if failures:
    print("FAILED:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(f"OK — all DORA self-checks passed ({len(dora.TESTS)} tests, {len(dora.QUESTIONS)} questions).")
