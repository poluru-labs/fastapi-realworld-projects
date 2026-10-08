from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.task_repository import TaskRecord, TaskRepository
from app.repositories.team_repository import TeamRecord, TeamRepository
from app.repositories.user_repository import UserRepository
from app.schemas.task import TaskCreate, TaskRead, TaskStatus, TaskUpdate
from app.schemas.team import MemberAdd, MemberRead, TeamCreate, TeamRead, TeamRole, TeamUpdate
from app.schemas.user import UserRead, UserRole

_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.TODO: {TaskStatus.IN_PROGRESS},
    TaskStatus.IN_PROGRESS: {TaskStatus.TODO, TaskStatus.DONE},
    TaskStatus.DONE: {TaskStatus.IN_PROGRESS},
}


class TeamService:
    def __init__(
        self,
        teams: TeamRepository,
        tasks: TaskRepository,
        users: UserRepository,
    ) -> None:
        self._teams = teams
        self._tasks = tasks
        self._users = users

    def list_teams(self, actor: UserRead) -> list[TeamRead]:
        if actor.role is UserRole.ADMIN:
            records = self._teams.list_all()
        else:
            records = self._teams.list_for_user(actor.id)
        return [self._team_read(record, actor) for record in records]

    def create_team(self, actor: UserRead, payload: TeamCreate) -> TeamRead:
        if self._teams.name_taken(payload.name):
            raise ConflictError(f"Team name '{payload.name}' already exists")
        record = self._teams.create(
            name=payload.name,
            description=payload.description,
            owner_id=actor.id,
        )
        return self._team_read(record, actor)

    def get_team(self, actor: UserRead, team_id: int) -> TeamRead:
        record = self._require_team(team_id)
        self._require_member(record, actor)
        return self._team_read(record, actor)

    def update_team(self, actor: UserRead, team_id: int, payload: TeamUpdate) -> TeamRead:
        record = self._require_team(team_id)
        self._require_owner(record, actor)
        previous_name = record.name
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is not None:
            if self._teams.name_taken(changes["name"], except_id=record.id):
                raise ConflictError(f"Team name '{changes['name']}' already exists")
            record.name = changes["name"]
        if "description" in changes and changes["description"] is not None:
            record.description = changes["description"]
        self._teams.save(record, previous_name=previous_name)
        return self._team_read(record, actor)

    def delete_team(self, actor: UserRead, team_id: int) -> None:
        record = self._require_team(team_id)
        self._require_owner(record, actor)
        self._tasks.delete_for_team(team_id)
        self._teams.delete(team_id)

    def list_members(self, actor: UserRead, team_id: int) -> list[MemberRead]:
        record = self._require_team(team_id)
        self._require_member(record, actor)
        return self._member_reads(team_id)

    def add_member(self, actor: UserRead, team_id: int, payload: MemberAdd) -> MemberRead:
        record = self._require_team(team_id)
        self._require_owner(record, actor)
        user = self._users.get_by_email(str(payload.email))
        if user is None or not user.is_active:
            raise NotFoundError("User", payload.email)
        if self._teams.role_of(team_id, user.id) is not None:
            raise ConflictError(f"{user.email} is already on this team")
        self._teams.add_member(team_id, user.id)
        return MemberRead(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            team_role=TeamRole.MEMBER,
        )

    def remove_member(self, actor: UserRead, team_id: int, user_id: int) -> None:
        record = self._require_team(team_id)
        self._require_owner(record, actor)
        role = self._teams.role_of(team_id, user_id)
        if role is None:
            raise NotFoundError("Member", user_id)
        if role is TeamRole.OWNER:
            raise ConflictError("Cannot remove the team owner")
        self._teams.remove_member(team_id, user_id)
        self._tasks.clear_assignee(team_id, user_id)

    def list_tasks(
        self,
        actor: UserRead,
        team_id: int,
        *,
        status: TaskStatus | None = None,
        assignee_id: int | None = None,
    ) -> list[TaskRead]:
        record = self._require_team(team_id)
        self._require_member(record, actor)
        rows = self._tasks.list_for_team(team_id, status=status, assignee_id=assignee_id)
        return [self._task_read(task) for task in rows]

    def get_task(self, actor: UserRead, team_id: int, task_id: int) -> TaskRead:
        record = self._require_team(team_id)
        self._require_member(record, actor)
        return self._task_read(self._require_task(team_id, task_id))

    def create_task(self, actor: UserRead, team_id: int, payload: TaskCreate) -> TaskRead:
        record = self._require_team(team_id)
        self._require_member(record, actor)
        assignee_id = None
        if payload.assignee_email is not None:
            assignee_id = self._require_assignee(team_id, str(payload.assignee_email))
        task = TaskRecord(
            id=self._tasks.allocate_id(),
            team_id=team_id,
            title=payload.title,
            description=payload.description,
            status=TaskStatus.TODO,
            assignee_id=assignee_id,
            created_by=actor.id,
            created_at=datetime.now(UTC),
        )
        self._tasks.add(task)
        return self._task_read(task)

    def update_task(
        self,
        actor: UserRead,
        team_id: int,
        task_id: int,
        payload: TaskUpdate,
    ) -> TaskRead:
        record = self._require_team(team_id)
        self._require_member(record, actor)
        task = self._require_task(team_id, task_id)
        changes = payload.model_dump(exclude_unset=True)
        if changes.get("title") is not None:
            task.title = changes["title"]
        if changes.get("description") is not None:
            task.description = changes["description"]
        if changes.get("clear_assignee"):
            task.assignee_id = None
        elif "assignee_email" in changes and changes["assignee_email"] is not None:
            task.assignee_id = self._require_assignee(team_id, str(changes["assignee_email"]))
        if changes.get("status") is not None:
            self._move_status(task, TaskStatus(changes["status"]))
        self._tasks.save(task)
        return self._task_read(task)

    def delete_task(self, actor: UserRead, team_id: int, task_id: int) -> None:
        record = self._require_team(team_id)
        self._require_member(record, actor)
        task = self._require_task(team_id, task_id)
        is_owner = self._teams.role_of(team_id, actor.id) is TeamRole.OWNER
        if actor.role is not UserRole.ADMIN and not is_owner and task.created_by != actor.id:
            raise ForbiddenError(
                "Only the creator, team owner, or a platform admin can delete this task"
            )
        self._tasks.delete(task.id)

    def _require_team(self, team_id: int) -> TeamRecord:
        record = self._teams.get(team_id)
        if record is None:
            raise NotFoundError("Team", team_id)
        return record

    def _require_member(self, team: TeamRecord, actor: UserRead) -> None:
        if actor.role is UserRole.ADMIN:
            return
        if self._teams.role_of(team.id, actor.id) is None:
            raise ForbiddenError("You are not a member of this team")

    def _require_owner(self, team: TeamRecord, actor: UserRead) -> None:
        if actor.role is UserRole.ADMIN:
            return
        if self._teams.role_of(team.id, actor.id) is not TeamRole.OWNER:
            raise ForbiddenError("Only the team owner can do that")

    def _require_task(self, team_id: int, task_id: int) -> TaskRecord:
        task = self._tasks.get(team_id, task_id)
        if task is None:
            raise NotFoundError("Task", task_id)
        return task

    def _require_assignee(self, team_id: int, email: str) -> int:
        user = self._users.get_by_email(email)
        if user is None or not user.is_active:
            raise NotFoundError("User", email)
        if self._teams.role_of(team_id, user.id) is None:
            raise ConflictError("Assignee is not a member of this team")
        return user.id

    def _move_status(self, task: TaskRecord, target: TaskStatus) -> None:
        if task.status is target:
            return
        allowed = _TRANSITIONS[task.status]
        if target not in allowed:
            raise ConflictError(f"Cannot move a task from {task.status.value} to {target.value}")
        task.status = target

    def _team_read(self, record: TeamRecord, actor: UserRead) -> TeamRead:
        return TeamRead(
            id=record.id,
            name=record.name,
            description=record.description,
            owner_id=record.owner_id,
            member_count=self._teams.member_count(record.id),
            team_role=self._teams.role_of(record.id, actor.id),
            created_at=record.created_at,
        )

    def _member_reads(self, team_id: int) -> list[MemberRead]:
        members: list[MemberRead] = []
        for user_id, role in self._teams.members(team_id):
            user = self._users.get_by_id(user_id)
            if user is None:
                continue
            members.append(
                MemberRead(
                    user_id=user.id,
                    email=user.email,
                    full_name=user.full_name,
                    team_role=role,
                )
            )
        return members

    def _task_read(self, task: TaskRecord) -> TaskRead:
        return TaskRead(
            id=task.id,
            team_id=task.team_id,
            title=task.title,
            description=task.description,
            status=task.status,
            assignee_id=task.assignee_id,
            created_by=task.created_by,
            created_at=task.created_at,
        )
