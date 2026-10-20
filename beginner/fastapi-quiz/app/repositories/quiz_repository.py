from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache

from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.quiz import QuizStatus


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class QuizRecord:
    id: int
    title: str
    description: str
    status: QuizStatus
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass
class QuestionRecord:
    id: int
    quiz_id: int
    prompt: str
    choices: list[str]
    correct_index: int
    position: int


_TRANSITIONS: dict[QuizStatus, set[QuizStatus]] = {
    QuizStatus.DRAFT: {QuizStatus.PUBLISHED},
    QuizStatus.PUBLISHED: {QuizStatus.DRAFT, QuizStatus.ARCHIVED},
    QuizStatus.ARCHIVED: {QuizStatus.DRAFT},
}


class QuizRepository:
    def __init__(self) -> None:
        now = _utcnow()
        self._quizzes: dict[int, QuizRecord] = {
            1: QuizRecord(
                id=1,
                title="Python basics",
                description="A short multiple-choice quiz for beginners.",
                status=QuizStatus.PUBLISHED,
                created_at=now,
                updated_at=now,
            ),
            2: QuizRecord(
                id=2,
                title="FastAPI draft",
                description="Work in progress — not on the public list.",
                status=QuizStatus.DRAFT,
                created_at=now,
                updated_at=now,
            ),
        }
        self._questions: dict[int, QuestionRecord] = {
            1: QuestionRecord(
                id=1,
                quiz_id=1,
                prompt="Which keyword defines a function in Python?",
                choices=["func", "def", "fn", "lambda only"],
                correct_index=1,
                position=1,
            ),
            2: QuestionRecord(
                id=2,
                quiz_id=1,
                prompt="What does FastAPI use for request validation?",
                choices=["Marshmallow", "Pydantic", "pickle", "CSV"],
                correct_index=1,
                position=2,
            ),
            3: QuestionRecord(
                id=3,
                quiz_id=1,
                prompt="HTTP status 404 usually means:",
                choices=["Success", "Not found", "Rate limited", "Upgrade required"],
                correct_index=1,
                position=3,
            ),
        }
        self._next_quiz_id = 3
        self._next_question_id = 4

    def list_quizzes(self, *, status: QuizStatus | None) -> list[QuizRecord]:
        rows = list(self._quizzes.values())
        if status is not None:
            rows = [quiz for quiz in rows if quiz.status is status]
        rows.sort(key=lambda quiz: (quiz.title.casefold(), quiz.id))
        return rows

    def get_quiz(self, quiz_id: int) -> QuizRecord:
        record = self._quizzes.get(quiz_id)
        if record is None:
            raise NotFoundError("Quiz", quiz_id)
        return record

    def create_quiz(self, *, title: str, description: str) -> QuizRecord:
        quiz_id = self._next_quiz_id
        self._next_quiz_id += 1
        record = QuizRecord(
            id=quiz_id,
            title=title,
            description=description,
            status=QuizStatus.DRAFT,
        )
        self._quizzes[quiz_id] = record
        return record

    def update_quiz(
        self,
        quiz_id: int,
        *,
        title: str | None,
        description: str | None,
    ) -> QuizRecord:
        record = self.get_quiz(quiz_id)
        if title is not None:
            record.title = title
        if description is not None:
            record.description = description
        record.updated_at = _utcnow()
        return record

    def transition(self, quiz_id: int, *, target: QuizStatus, message: str) -> QuizRecord:
        record = self.get_quiz(quiz_id)
        allowed = _TRANSITIONS[record.status]
        if target not in allowed:
            raise ConflictError(f"{message}. This quiz is {record.status.value}")
        if target is QuizStatus.PUBLISHED:
            questions = self.list_questions(quiz_id)
            if not questions:
                raise ConflictError("Add at least one question before publishing")
        record.status = target
        record.updated_at = _utcnow()
        return record

    def list_questions(self, quiz_id: int) -> list[QuestionRecord]:
        self.get_quiz(quiz_id)
        rows = [question for question in self._questions.values() if question.quiz_id == quiz_id]
        rows.sort(key=lambda question: question.position)
        return rows

    def get_question(self, question_id: int) -> QuestionRecord:
        record = self._questions.get(question_id)
        if record is None:
            raise NotFoundError("Question", question_id)
        return record

    def _require_draft(self, quiz_id: int) -> QuizRecord:
        quiz = self.get_quiz(quiz_id)
        if quiz.status is not QuizStatus.DRAFT:
            raise ConflictError("Questions can only be edited while the quiz is a draft")
        return quiz

    def add_question(
        self,
        quiz_id: int,
        *,
        prompt: str,
        choices: list[str],
        correct_index: int,
    ) -> QuestionRecord:
        self._require_draft(quiz_id)
        if correct_index >= len(choices):
            raise ConflictError("correct_index must point at one of the choices")
        position = len(self.list_questions(quiz_id)) + 1
        question_id = self._next_question_id
        self._next_question_id += 1
        record = QuestionRecord(
            id=question_id,
            quiz_id=quiz_id,
            prompt=prompt,
            choices=list(choices),
            correct_index=correct_index,
            position=position,
        )
        self._questions[question_id] = record
        self._quizzes[quiz_id].updated_at = _utcnow()
        return record

    def update_question(
        self,
        question_id: int,
        *,
        prompt: str | None,
        choices: list[str] | None,
        correct_index: int | None,
    ) -> QuestionRecord:
        record = self.get_question(question_id)
        self._require_draft(record.quiz_id)
        next_choices = list(choices) if choices is not None else list(record.choices)
        next_index = correct_index if correct_index is not None else record.correct_index
        if next_index >= len(next_choices):
            raise ConflictError("correct_index must point at one of the choices")
        if prompt is not None:
            record.prompt = prompt
        if choices is not None:
            record.choices = next_choices
        record.correct_index = next_index
        self._quizzes[record.quiz_id].updated_at = _utcnow()
        return record

    def delete_question(self, question_id: int) -> None:
        record = self.get_question(question_id)
        self._require_draft(record.quiz_id)
        del self._questions[question_id]
        remaining = self.list_questions(record.quiz_id)
        for index, question in enumerate(remaining, start=1):
            question.position = index
        self._quizzes[record.quiz_id].updated_at = _utcnow()

    def question_count(self, quiz_id: int) -> int:
        return len(self.list_questions(quiz_id))


@lru_cache
def get_quiz_repository() -> QuizRepository:
    return QuizRepository()
