from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.quiz_repository import QuizRepository
from app.schemas.quiz import (
    QuestionAuthorRead,
    QuestionCreate,
    QuestionPlayerRead,
    QuestionResult,
    QuestionUpdate,
    QuizAuthorDetail,
    QuizCreate,
    QuizPlayerDetail,
    QuizRead,
    QuizStatus,
    QuizSubmit,
    QuizSubmitResult,
    QuizUpdate,
)


class QuizService:
    def __init__(self, repo: QuizRepository) -> None:
        self._repo = repo

    def list_quizzes(self, *, status: QuizStatus | None) -> list[QuizRead]:
        return [self._to_read(quiz) for quiz in self._repo.list_quizzes(status=status)]

    def get_quiz_for_author(self, quiz_id: int) -> QuizAuthorDetail:
        quiz = self._repo.get_quiz(quiz_id)
        questions = self._repo.list_questions(quiz_id)
        return QuizAuthorDetail(
            **self._to_read(quiz).model_dump(),
            questions=[QuestionAuthorRead.model_validate(q) for q in questions],
        )

    def get_quiz_for_player(self, quiz_id: int) -> QuizPlayerDetail:
        quiz = self._repo.get_quiz(quiz_id)
        if quiz.status is not QuizStatus.PUBLISHED:
            raise NotFoundError("Quiz", quiz_id)
        questions = self._repo.list_questions(quiz_id)
        return QuizPlayerDetail(
            **self._to_read(quiz).model_dump(),
            questions=[
                QuestionPlayerRead(
                    id=q.id,
                    quiz_id=q.quiz_id,
                    prompt=q.prompt,
                    choices=list(q.choices),
                    position=q.position,
                )
                for q in questions
            ],
        )

    def create_quiz(self, payload: QuizCreate) -> QuizRead:
        record = self._repo.create_quiz(title=payload.title, description=payload.description)
        return self._to_read(record)

    def update_quiz(self, quiz_id: int, payload: QuizUpdate) -> QuizRead:
        fields = payload.model_dump(exclude_unset=True)
        record = self._repo.update_quiz(
            quiz_id,
            title=fields.get("title"),
            description=fields.get("description"),
        )
        return self._to_read(record)

    def publish(self, quiz_id: int) -> QuizRead:
        record = self._repo.transition(
            quiz_id,
            target=QuizStatus.PUBLISHED,
            message="Only a draft can be published",
        )
        return self._to_read(record)

    def unpublish(self, quiz_id: int) -> QuizRead:
        return self._to_read(
            self._repo.transition(
                quiz_id,
                target=QuizStatus.DRAFT,
                message="Only a published quiz can be unpublished",
            )
        )

    def archive(self, quiz_id: int) -> QuizRead:
        return self._to_read(
            self._repo.transition(
                quiz_id,
                target=QuizStatus.ARCHIVED,
                message="Only a published quiz can be archived",
            )
        )

    def restore(self, quiz_id: int) -> QuizRead:
        return self._to_read(
            self._repo.transition(
                quiz_id,
                target=QuizStatus.DRAFT,
                message="Only an archived quiz can be restored",
            )
        )

    def add_question(self, quiz_id: int, payload: QuestionCreate) -> QuestionAuthorRead:
        record = self._repo.add_question(
            quiz_id,
            prompt=payload.prompt,
            choices=payload.choices,
            correct_index=payload.correct_index,
        )
        return QuestionAuthorRead.model_validate(record)

    def update_question(self, question_id: int, payload: QuestionUpdate) -> QuestionAuthorRead:
        fields = payload.model_dump(exclude_unset=True)
        record = self._repo.update_question(
            question_id,
            prompt=fields.get("prompt"),
            choices=fields.get("choices"),
            correct_index=fields.get("correct_index"),
        )
        return QuestionAuthorRead.model_validate(record)

    def delete_question(self, question_id: int) -> None:
        self._repo.delete_question(question_id)

    def submit(self, quiz_id: int, payload: QuizSubmit) -> QuizSubmitResult:
        quiz = self._repo.get_quiz(quiz_id)
        if quiz.status is not QuizStatus.PUBLISHED:
            raise ConflictError("Only published quizzes accept submissions")
        questions = {q.id: q for q in self._repo.list_questions(quiz_id)}
        if not questions:
            raise ConflictError("This quiz has no questions")
        results: list[QuestionResult] = []
        score = 0
        for answer in payload.answers:
            question = questions.get(answer.question_id)
            if question is None:
                raise ConflictError(f"Question {answer.question_id} is not part of this quiz")
            if answer.choice_index >= len(question.choices):
                raise ConflictError(f"Invalid choice_index for question {answer.question_id}")
            correct = answer.choice_index == question.correct_index
            if correct:
                score += 1
            results.append(
                QuestionResult(
                    question_id=question.id,
                    correct=correct,
                    chosen_index=answer.choice_index,
                    correct_index=question.correct_index,
                )
            )
        total = len(questions)
        percentage = round(100.0 * score / total, 2)
        return QuizSubmitResult(
            quiz_id=quiz_id,
            participant_name=payload.participant_name,
            score=score,
            total_questions=total,
            percentage=percentage,
            results=results,
        )

    def _to_read(self, quiz) -> QuizRead:
        return QuizRead(
            id=quiz.id,
            title=quiz.title,
            description=quiz.description,
            status=quiz.status,
            question_count=self._repo.question_count(quiz.id),
            created_at=quiz.created_at,
            updated_at=quiz.updated_at,
        )
