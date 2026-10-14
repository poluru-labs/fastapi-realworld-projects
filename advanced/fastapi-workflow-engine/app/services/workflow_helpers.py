from app.core.exceptions import ConflictError
from app.models.workflow import WorkflowDefinition
from app.schemas.user import UserRead, UserRole
from app.schemas.workflow import (
    DefinitionStatus,
    TransitionSpec,
    WorkflowDefinitionCreate,
    WorkflowDefinitionUpdate,
)


def parse_transitions(raw: list[dict]) -> list[TransitionSpec]:
    return [TransitionSpec.model_validate(item) for item in raw]


def definition_can_view(actor: UserRead | None, row: WorkflowDefinition) -> bool:
    if row.status == DefinitionStatus.PUBLISHED.value:
        return True
    if actor is None:
        return False
    return actor.role is UserRole.ADMIN


def actor_may_fire(actor: UserRead, edge: TransitionSpec) -> bool:
    if not edge.roles:
        return True
    if actor.role is UserRole.ADMIN:
        return True
    return actor.role in edge.roles


def find_transition(
    definition: WorkflowDefinition,
    *,
    action: str,
    from_state: str,
) -> TransitionSpec:
    for raw in definition.transitions:
        edge = TransitionSpec.model_validate(raw)
        if edge.action == action and edge.from_state == from_state:
            return edge
    raise ConflictError(
        f"Action {action!r} is not valid from state {from_state!r} for this workflow"
    )


def merge_definition_update(
    row: WorkflowDefinition, payload: WorkflowDefinitionUpdate
) -> WorkflowDefinitionCreate:
    data = {
        "slug": row.slug,
        "name": row.name,
        "description": row.description,
        "initial_state": row.initial_state,
        "states": list(row.states),
        "transitions": parse_transitions(row.transitions),
        "terminal_states": list(row.terminal_states),
    }
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        data[key] = value
    return WorkflowDefinitionCreate.model_validate(data)


def ensure_draft(row: WorkflowDefinition) -> None:
    if row.status != DefinitionStatus.DRAFT.value:
        raise ConflictError("Only draft definitions can be edited")
