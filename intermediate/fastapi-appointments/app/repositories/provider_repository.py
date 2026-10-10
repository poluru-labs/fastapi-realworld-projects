from dataclasses import dataclass


@dataclass
class ProviderRecord:
    id: int
    name: str
    specialty: str
    is_active: bool


def _seed_providers() -> dict[int, ProviderRecord]:
    return {
        1: ProviderRecord(
            id=1,
            name="Dr Ada Lovelace",
            specialty="General practice",
            is_active=True,
        ),
        2: ProviderRecord(
            id=2,
            name="Dr Grace Hopper",
            specialty="Follow-up visits",
            is_active=True,
        ),
    }


class ProviderRepository:
    def __init__(self) -> None:
        self._providers = dict(_seed_providers())
        self._next_id = max(self._providers.keys(), default=0) + 1

    def list_all(self) -> list[ProviderRecord]:
        return list(self._providers.values())

    def get(self, provider_id: int) -> ProviderRecord | None:
        return self._providers.get(provider_id)

    def add(self, record: ProviderRecord) -> ProviderRecord:
        self._providers[record.id] = record
        return record

    def allocate_id(self) -> int:
        provider_id = self._next_id
        self._next_id += 1
        return provider_id

    def save(self, record: ProviderRecord) -> None:
        self._providers[record.id] = record
