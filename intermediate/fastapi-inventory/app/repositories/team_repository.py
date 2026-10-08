from dataclasses import dataclass
from datetime import UTC, datetime

from app.schemas.team import TeamRole


@dataclass
class TeamRecord:
    id: int
    name: str
    description: str
    owner_id: int
    created_at: datetime


class TeamRepository:
    """In-memory teams and memberships. Reset when the process restarts."""

    def __init__(self) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        self._teams: dict[int, TeamRecord] = {
            1: TeamRecord(
                id=1,
                name="Platform",
                description="Seed team owned by the admin account.",
                owner_id=1,
                created_at=now,
            )
        }
        self._members: dict[int, dict[int, TeamRole]] = {1: {1: TeamRole.OWNER}}
        self._names = {record.name.casefold(): record.id for record in self._teams.values()}
        self._next_id = 2

    def list_all(self) -> list[TeamRecord]:
        return sorted(self._teams.values(), key=lambda team: team.id)

    def list_for_user(self, user_id: int) -> list[TeamRecord]:
        team_ids = [team_id for team_id, members in self._members.items() if user_id in members]
        return [self._teams[team_id] for team_id in sorted(team_ids)]

    def get(self, team_id: int) -> TeamRecord | None:
        return self._teams.get(team_id)

    def name_taken(self, name: str, *, except_id: int | None = None) -> bool:
        existing = self._names.get(name.casefold())
        return existing is not None and existing != except_id

    def create(self, *, name: str, description: str, owner_id: int) -> TeamRecord:
        record = TeamRecord(
            id=self._next_id,
            name=name,
            description=description,
            owner_id=owner_id,
            created_at=datetime.now(UTC),
        )
        self._teams[record.id] = record
        self._members[record.id] = {owner_id: TeamRole.OWNER}
        self._names[name.casefold()] = record.id
        self._next_id += 1
        return record

    def save(self, record: TeamRecord, *, previous_name: str) -> None:
        if previous_name.casefold() != record.name.casefold():
            self._names.pop(previous_name.casefold(), None)
            self._names[record.name.casefold()] = record.id
        self._teams[record.id] = record

    def delete(self, team_id: int) -> None:
        record = self._teams.pop(team_id, None)
        self._members.pop(team_id, None)
        if record is not None:
            self._names.pop(record.name.casefold(), None)

    def role_of(self, team_id: int, user_id: int) -> TeamRole | None:
        return self._members.get(team_id, {}).get(user_id)

    def members(self, team_id: int) -> list[tuple[int, TeamRole]]:
        membership = self._members.get(team_id, {})
        return sorted(membership.items(), key=lambda item: item[0])

    def member_count(self, team_id: int) -> int:
        return len(self._members.get(team_id, {}))

    def add_member(self, team_id: int, user_id: int) -> None:
        self._members[team_id][user_id] = TeamRole.MEMBER

    def remove_member(self, team_id: int, user_id: int) -> None:
        self._members[team_id].pop(user_id, None)
