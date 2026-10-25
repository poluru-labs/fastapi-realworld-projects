from app.core.exceptions import NotFoundError
from app.repositories.poll_repository import PollRepository
from app.schemas.poll import PollCreate, PollRead, PollUpdate, VoteCreate


class PollService:
    def __init__(self, repository: PollRepository) -> None:
        self._repo = repository

    def list_polls(self) -> list[PollRead]:
        return self._repo.list_all()

    def get_poll(self, poll_id: int) -> PollRead:
        poll = self._repo.get(poll_id)
        if poll is None:
            raise NotFoundError("Poll", poll_id)
        return poll

    def create_poll(self, payload: PollCreate) -> PollRead:
        return self._repo.create(payload)

    def replace_poll(self, poll_id: int, payload: PollCreate) -> PollRead:
        poll = self._repo.replace(poll_id, payload)
        if poll is None:
            raise NotFoundError("Poll", poll_id)
        return poll

    def update_poll(self, poll_id: int, payload: PollUpdate) -> PollRead:
        poll = self._repo.update(poll_id, payload)
        if poll is None:
            raise NotFoundError("Poll", poll_id)
        return poll

    def delete_poll(self, poll_id: int) -> PollRead:
        poll = self._repo.delete(poll_id)
        if poll is None:
            raise NotFoundError("Poll", poll_id)
        return poll

    def cast_vote(self, poll_id: int, payload: VoteCreate) -> PollRead:
        poll, option_found = self._repo.vote(poll_id, payload.option_id)
        if poll is None:
            raise NotFoundError("Poll", poll_id)
        if not option_found:
            raise NotFoundError("Poll option", payload.option_id)
        return poll
