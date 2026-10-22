from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.experiment_tokens import hash_experiment_token
from app.models.experimentation import Experiment, ExperimentEvent, ExperimentVariant
from app.schemas.experimentation import EventType, ExperimentStatus

SEED_EXPERIMENT_TOKEN = "seed-token-checkout-button"


async def seed_reference_data(session: AsyncSession) -> None:
    existing = await session.scalar(
        select(Experiment).where(Experiment.key == "checkout-button")
    )
    if existing is not None:
        return

    now = datetime.now(UTC)
    experiment = Experiment(
        key="checkout-button",
        name="Checkout button color",
        description="Green vs blue primary button on checkout.",
        status=ExperimentStatus.RUNNING.value,
        ingest_token_hash=hash_experiment_token(SEED_EXPERIMENT_TOKEN),
        started_at=now,
        stopped_at=None,
        created_at=now,
        updated_at=now,
    )
    draft = Experiment(
        key="pricing-page-test",
        name="Pricing layout draft",
        description="Not started — for exploring draft-only variant APIs.",
        status=ExperimentStatus.DRAFT.value,
        ingest_token_hash=hash_experiment_token("seed-token-pricing-draft"),
        started_at=None,
        stopped_at=None,
        created_at=now,
        updated_at=now,
    )
    session.add_all([experiment, draft])
    await session.flush()

    session.add_all(
        [
            ExperimentVariant(
                experiment_id=experiment.id,
                key="control",
                name="Blue button",
                weight=50,
                created_at=now,
            ),
            ExperimentVariant(
                experiment_id=experiment.id,
                key="treatment",
                name="Green button",
                weight=50,
                created_at=now,
            ),
        ]
    )

    events = [
        ExperimentEvent(
            experiment_id=experiment.id,
            subject_id="user-100",
            event_type=EventType.EXPOSURE.value,
            variant_key="control",
            occurred_at=now,
            properties={"page": "checkout"},
            dedupe_key="exp-user-100",
            ingested_at=now,
        ),
        ExperimentEvent(
            experiment_id=experiment.id,
            subject_id="user-100",
            event_type=EventType.CONVERSION.value,
            variant_key="control",
            occurred_at=now,
            properties={"order_id": "ord-1"},
            dedupe_key="conv-user-100",
            ingested_at=now,
        ),
        ExperimentEvent(
            experiment_id=experiment.id,
            subject_id="user-200",
            event_type=EventType.EXPOSURE.value,
            variant_key="treatment",
            occurred_at=now,
            properties={"page": "checkout"},
            dedupe_key="exp-user-200",
            ingested_at=now,
        ),
    ]
    session.add_all(events)
    await session.commit()
