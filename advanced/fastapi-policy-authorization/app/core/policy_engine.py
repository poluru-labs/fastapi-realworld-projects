from enum import StrEnum
from typing import Any

from app.schemas.policy import PolicyEffect


class Clearance(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SECRET = "secret"


_CLEARANCE_RANK = {
    Clearance.PUBLIC.value: 0,
    Clearance.INTERNAL.value: 1,
    Clearance.SECRET.value: 2,
}


def _rank(level: str) -> int:
    return _CLEARANCE_RANK.get(level, -1)


def action_matches(rule_action: str, requested: str) -> bool:
    if rule_action == requested:
        return True
    if rule_action.endswith(":*"):
        prefix = rule_action[:-1]
        return requested.startswith(prefix)
    return False


def resource_matches(rule_resource: str, requested: str) -> bool:
    if rule_resource == requested:
        return True
    if rule_resource.endswith("*"):
        prefix = rule_resource[:-1]
        return requested.startswith(prefix)
    return False


def clearance_allows(
    *,
    user_clearance: str,
    required: str | None,
    resource_classification: str | None,
) -> bool:
    if required:
        if _rank(user_clearance) < _rank(required):
            return False
    if resource_classification:
        if _rank(user_clearance) < _rank(resource_classification):
            return False
    return True


def evaluate_policies(
    *,
    rules: list[dict[str, Any]],
    user_roles: set[str],
    user_clearance: str,
    action: str,
    resource: str,
    resource_attributes: dict[str, Any] | None,
) -> tuple[bool, str | None]:
    """Return (allowed, matched_rule_name). Default deny when nothing matches."""
    classification = None
    if resource_attributes:
        raw = resource_attributes.get("classification")
        if isinstance(raw, str):
            classification = raw

    matching: list[dict[str, Any]] = []
    for rule in rules:
        role_ok = not rule["roles"] or user_roles.intersection(set(rule["roles"]))
        if not role_ok:
            continue
        actions: list[str] = rule["actions"]
        resources: list[str] = rule["resources"]
        if not any(action_matches(item, action) for item in actions):
            continue
        if not any(resource_matches(item, resource) for item in resources):
            continue
        required = rule.get("required_clearance")
        if not clearance_allows(
            user_clearance=user_clearance,
            required=required,
            resource_classification=classification,
        ):
            continue
        matching.append(rule)

    if not matching:
        return False, None

    matching.sort(key=lambda row: int(row["priority"]), reverse=True)
    for rule in matching:
        if rule["effect"] == PolicyEffect.DENY.value:
            return False, rule["name"]

    for rule in matching:
        if rule["effect"] == PolicyEffect.ALLOW.value:
            return True, rule["name"]

    return False, None
