from app.schemas.poll import PollCreate, PollOptionRead, PollRead, PollUpdate


def _options_from_texts(texts: list[str]) -> list[PollOptionRead]:
    return [
        PollOptionRead(id=index, text=text, votes=0)
        for index, text in enumerate(texts, start=1)
    ]


_MOCK_POLLS: dict[int, PollRead] = {
    1: PollRead(
        id=1,
        question="What is your favorite programming language?",
        options=[
            PollOptionRead(id=1, text="Python", votes=3),
            PollOptionRead(id=2, text="JavaScript", votes=1),
            PollOptionRead(id=3, text="Go", votes=0),
        ],
    ),
    2: PollRead(
        id=2,
        question="Best time for team standup?",
        options=[
            PollOptionRead(id=1, text="Morning", votes=5),
            PollOptionRead(id=2, text="Afternoon", votes=2),
        ],
    ),
}


class PollRepository:
    def __init__(self) -> None:
        self._polls = dict(_MOCK_POLLS)
        self._next_id = max(self._polls.keys(), default=0) + 1

    def list_all(self) -> list[PollRead]:
        return list(self._polls.values())

    def get(self, poll_id: int) -> PollRead | None:
        return self._polls.get(poll_id)

    def create(self, payload: PollCreate) -> PollRead:
        poll = PollRead(
            id=self._next_id,
            question=payload.question,
            options=_options_from_texts(payload.options),
        )
        self._polls[self._next_id] = poll
        self._next_id += 1
        return poll

    def replace(self, poll_id: int, payload: PollCreate) -> PollRead | None:
        if poll_id not in self._polls:
            return None
        poll = PollRead(
            id=poll_id,
            question=payload.question,
            options=_options_from_texts(payload.options),
        )
        self._polls[poll_id] = poll
        return poll

    def update(self, poll_id: int, payload: PollUpdate) -> PollRead | None:
        existing = self._polls.get(poll_id)
        if existing is None:
            return None
        data = existing.model_dump()
        updates = payload.model_dump(exclude_unset=True)
        if "options" in updates and updates["options"] is not None:
            new_options = _options_from_texts(updates["options"])
            data["options"] = [option.model_dump() for option in new_options]
            del updates["options"]
        data.update(updates)
        poll = PollRead(**data)
        self._polls[poll_id] = poll
        return poll

    def delete(self, poll_id: int) -> PollRead | None:
        return self._polls.pop(poll_id, None)

    def vote(self, poll_id: int, option_id: int) -> tuple[PollRead | None, bool]:
        """Return (poll, option_found). poll is None when the poll id is missing."""
        poll = self._polls.get(poll_id)
        if poll is None:
            return None, False

        option_found = any(option.id == option_id for option in poll.options)
        if not option_found:
            return poll, False

        updated_options = [
            option.model_copy(update={"votes": option.votes + 1})
            if option.id == option_id
            else option
            for option in poll.options
        ]
        updated = poll.model_copy(update={"options": updated_options})
        self._polls[poll_id] = updated
        return updated, True
