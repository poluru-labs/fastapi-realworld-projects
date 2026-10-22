from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import AdminKey, DbSession
from app.schemas.experimentation import (
    EXPERIMENT_KEY_PATTERN,
    AssignmentRead,
    ExperimentCreate,
    ExperimentDetail,
    ExperimentProvisioned,
    ExperimentRead,
    ExperimentResults,
    VariantCreate,
    VariantRead,
)
from app.services.experiment_service import ExperimentService

router = APIRouter()

ExperimentKey = Annotated[
    str,
    Path(pattern=EXPERIMENT_KEY_PATTERN.pattern, min_length=2, max_length=64),
]


@router.get(
    "",
    response_model=list[ExperimentRead],
    summary="List experiments",
    description="Admin key required.",
)
async def list_experiments(_: AdminKey, session: DbSession) -> list[ExperimentRead]:
    return await ExperimentService(session).list_experiments()


@router.post(
    "",
    response_model=ExperimentProvisioned,
    status_code=status.HTTP_201_CREATED,
    summary="Provision an experiment",
    description="Returns a one-time **ingest_token** for SDK event POSTs.",
)
async def provision_experiment(
    _: AdminKey,
    session: DbSession,
    payload: ExperimentCreate,
) -> ExperimentProvisioned:
    return await ExperimentService(session).provision(payload)


@router.get(
    "/{experiment_key}",
    response_model=ExperimentDetail,
    summary="Experiment detail with variants",
)
async def get_experiment(
    _: AdminKey,
    session: DbSession,
    experiment_key: ExperimentKey,
) -> ExperimentDetail:
    return await ExperimentService(session).get_detail(experiment_key)


@router.post(
    "/{experiment_key}/variants",
    response_model=VariantRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a variant",
    description="Draft only. Weights should sum to 100 before `start`.",
)
async def add_variant(
    _: AdminKey,
    session: DbSession,
    experiment_key: ExperimentKey,
    payload: VariantCreate,
) -> VariantRead:
    return await ExperimentService(session).add_variant(experiment_key, payload)


@router.post(
    "/{experiment_key}/start",
    response_model=ExperimentRead,
    summary="Start an experiment",
    responses={409: {"description": "Not draft or invalid weights."}},
)
async def start_experiment(
    _: AdminKey,
    session: DbSession,
    experiment_key: ExperimentKey,
) -> ExperimentRead:
    return await ExperimentService(session).start(experiment_key)


@router.post(
    "/{experiment_key}/stop",
    response_model=ExperimentRead,
    summary="Stop a running experiment",
)
async def stop_experiment(
    _: AdminKey,
    session: DbSession,
    experiment_key: ExperimentKey,
) -> ExperimentRead:
    return await ExperimentService(session).stop(experiment_key)


@router.get(
    "/{experiment_key}/assignment",
    response_model=AssignmentRead,
    summary="Deterministic variant assignment",
    description=(
        "No auth required. Uses stable hashing on `subject_id` and variant weights. "
        "Only **running** experiments return data; others **404**."
    ),
)
async def get_assignment(
    session: DbSession,
    experiment_key: ExperimentKey,
    subject_id: Annotated[str, Query(min_length=1, max_length=128)],
) -> AssignmentRead:
    return await ExperimentService(session).assignment(experiment_key, subject_id)


@router.get(
    "/{experiment_key}/results",
    response_model=ExperimentResults,
    summary="Exposure and conversion stats",
    description="Admin key required. Counts events in the rolling window by `occurred_at`.",
)
async def get_results(
    _: AdminKey,
    session: DbSession,
    experiment_key: ExperimentKey,
    window_minutes: Annotated[int, Query(ge=1, le=10_080)] = 60,
) -> ExperimentResults:
    return await ExperimentService(session).results(
        experiment_key,
        window_minutes=window_minutes,
    )
