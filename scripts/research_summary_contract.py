"""Typed render-payload contract for research-summary-data.json.

Validates the payload's shape (closed field sets, no null/dict where a scalar
is required, enum values, duplicate IDs, scenario-probability arithmetic, and
distribution-mode source restrictions) and serializes it to canonical JSON.
Source-level concerns (missing case files, stale/blocked stage status) belong
to scripts/build_research_summary.py, not this module.
"""

import json
import unicodedata
from dataclasses import dataclass

SCHEMA_VERSION = 1
TEMPLATE_VERSION = 1
DISTRIBUTIONS = ("local", "shareable")
FACT_STATES = ("ready", "unavailable")

TOP_LEVEL_FIELDS = (
    "schema_version", "template_version", "case_id", "locale", "timezone", "as_of",
    "distribution", "identity", "current_view", "kpis", "expectation_gaps",
    "pricing_stage", "egg_theory", "evidence_timeline", "kill_criteria", "scenarios",
    "watch_items", "open_questions", "sources", "source_manifest",
)
IDENTITY_FIELDS = ("ticker", "company_name", "market", "currency")
CURRENT_VIEW_FIELDS = ("headline", "summary", "stance", "disclaimer")
FACT_FIELDS = {"value", "unit", "period", "state", "source_ref", "reason"}


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str


def _check_required_string(obj, key, path, issues):
    value = obj.get(key)
    if value is None:
        issues.append(ValidationIssue(f"{path}.{key}", f"{key} must not be null"))
    elif isinstance(value, (dict, list)):
        issues.append(ValidationIssue(f"{path}.{key}", f"{key} must be a scalar, not {type(value).__name__}"))
    elif not isinstance(value, str):
        issues.append(ValidationIssue(f"{path}.{key}", f"{key} must be a string"))


def _check_object_shape(obj, allowed_fields, path, issues):
    unknown = set(obj) - set(allowed_fields)
    for key in sorted(unknown):
        issues.append(ValidationIssue(f"{path}.{key}", f"unknown field: {key}"))
    for key in allowed_fields:
        if key not in obj:
            issues.append(ValidationIssue(f"{path}.{key}", f"missing required field: {key}"))


def _validate_fact(fact, path, issues):
    if not isinstance(fact, dict):
        issues.append(ValidationIssue(path, "fact must be an object"))
        return
    for key in sorted(set(fact) - FACT_FIELDS):
        issues.append(ValidationIssue(f"{path}.{key}", f"unknown field: {key}"))
    state = fact.get("state")
    if state not in FACT_STATES:
        issues.append(ValidationIssue(f"{path}.state", f"state must be one of {FACT_STATES}, got {state!r}"))
    if state == "unavailable" and not fact.get("reason"):
        issues.append(ValidationIssue(f"{path}.reason", "unavailable fact must include a non-empty reason"))
    if isinstance(fact.get("value"), dict):
        issues.append(ValidationIssue(f"{path}.value", "value must not be a dict"))


def validate_summary(payload):
    issues = []

    if not isinstance(payload, dict):
        return [ValidationIssue("$", "payload must be an object")]

    for key in sorted(set(payload) - set(TOP_LEVEL_FIELDS)):
        issues.append(ValidationIssue(f"$.{key}", f"unknown top-level field: {key}"))
    for key in TOP_LEVEL_FIELDS:
        if key not in payload:
            issues.append(ValidationIssue(f"$.{key}", f"missing required top-level field: {key}"))

    if payload.get("schema_version") != SCHEMA_VERSION:
        issues.append(ValidationIssue("$.schema_version", f"schema_version must be {SCHEMA_VERSION}"))
    if payload.get("template_version") != TEMPLATE_VERSION:
        issues.append(ValidationIssue("$.template_version", f"template_version must be {TEMPLATE_VERSION}"))
    if payload.get("distribution") not in DISTRIBUTIONS:
        issues.append(ValidationIssue("$.distribution", f"distribution must be one of {DISTRIBUTIONS}"))

    identity = payload.get("identity")
    if isinstance(identity, dict):
        _check_object_shape(identity, IDENTITY_FIELDS, "$.identity", issues)
    elif identity is not None:
        issues.append(ValidationIssue("$.identity", "identity must be an object"))

    current_view = payload.get("current_view")
    if isinstance(current_view, dict):
        _check_object_shape(current_view, CURRENT_VIEW_FIELDS, "$.current_view", issues)
        for field in CURRENT_VIEW_FIELDS:
            if field in current_view:
                _check_required_string(current_view, field, "$.current_view", issues)
    elif current_view is not None:
        issues.append(ValidationIssue("$.current_view", "current_view must be an object"))

    for index, kpi in enumerate(payload.get("kpis") or []):
        path = f"$.kpis[{index}]"
        if not isinstance(kpi, dict):
            issues.append(ValidationIssue(path, "kpi must be an object"))
            continue
        _validate_fact(kpi.get("fact"), f"{path}.fact", issues)

    seen_question_ids = set()
    for index, question in enumerate(payload.get("open_questions") or []):
        path = f"$.open_questions[{index}]"
        qid = question.get("id") if isinstance(question, dict) else None
        if qid in seen_question_ids:
            issues.append(ValidationIssue(path, f"duplicate open question id: {qid}"))
        seen_question_ids.add(qid)

    scenarios = payload.get("scenarios") or []
    scenario_values = []
    for scenario in scenarios:
        fact = scenario.get("probability") if isinstance(scenario, dict) else None
        if isinstance(fact, dict):
            _validate_fact(fact, "$.scenarios[].probability", issues)
            if fact.get("state") == "ready" and isinstance(fact.get("value"), (int, float)) and not isinstance(fact.get("value"), bool):
                scenario_values.append(fact["value"])
    if scenarios and len(scenario_values) == len(scenarios):
        total = sum(scenario_values)
        if abs(total - 100) > 0.01:
            issues.append(ValidationIssue("$.scenarios", f"scenario probabilities must sum to 100, got {total}"))

    if payload.get("distribution") == "shareable":
        for index, source in enumerate(payload.get("sources") or []):
            if isinstance(source, dict) and source.get("restricted"):
                issues.append(
                    ValidationIssue(
                        f"$.sources[{index}]",
                        f"restricted source not allowed in shareable distribution: {source.get('name')!r}",
                    )
                )

    return issues


def _normalize(value):
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, dict):
        return {key: _normalize(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def canonical_json(payload):
    return json.dumps(_normalize(payload), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
