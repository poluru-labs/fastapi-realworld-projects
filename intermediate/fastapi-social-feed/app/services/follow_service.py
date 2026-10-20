from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.follow_repository import FollowRepository
from app.repositories.user_repository import UserRecord, UserRepository
from app.schemas.social import FollowCounts, FollowList, UserPublicProfile
from app.schemas.user import UserRead


class FollowService:
    def __init__(self, *, follows: FollowRepository, users: UserRepository) -> None:
        self._follows = follows
        self._users = users

    def follow(self, actor: UserRead, target_user_id: int) -> FollowCounts:
        self._require_user(target_user_id)
        if actor.id == target_user_id:
            raise ConflictError("You cannot follow yourself")
        if self._follows.is_following(actor.id, target_user_id):
            raise ConflictError("You already follow this account")
        self._follows.follow(actor.id, target_user_id)
        return self.counts_for(target_user_id)

    def unfollow(self, actor: UserRead, target_user_id: int) -> FollowCounts:
        self._require_user(target_user_id)
        if not self._follows.is_following(actor.id, target_user_id):
            raise ConflictError("You are not following this account")
        self._follows.unfollow(actor.id, target_user_id)
        return self.counts_for(target_user_id)

    def list_followers(self, user_id: int) -> FollowList:
        self._require_user(user_id)
        ids = self._follows.list_followers(user_id)
        return FollowList(items=[self._to_read(user_id) for user_id in ids], total=len(ids))

    def list_following(self, user_id: int) -> FollowList:
        self._require_user(user_id)
        ids = self._follows.list_following(user_id)
        return FollowList(items=[self._to_read(user_id) for user_id in ids], total=len(ids))

    def profile(self, actor: UserRead | None, user_id: int) -> UserPublicProfile:
        user = self._require_user(user_id)
        followed = False
        if actor is not None:
            followed = self._follows.is_following(actor.id, user_id)
        return UserPublicProfile(
            user=user.to_read(),
            counts=self.counts_for(user_id),
            followed_by_me=followed,
        )

    def counts_for(self, user_id: int) -> FollowCounts:
        return FollowCounts(
            followers=self._follows.follower_count(user_id),
            following=self._follows.following_count(user_id),
        )

    def is_following(self, follower_id: int, following_id: int) -> bool:
        return self._follows.is_following(follower_id, following_id)

    def _to_read(self, user_id: int) -> UserRead:
        record = self._require_user(user_id)
        return record.to_read()

    def _require_user(self, user_id: int) -> UserRecord:
        record = self._users.get_by_id(user_id)
        if record is None or not record.is_active:
            raise NotFoundError("User", str(user_id))
        return record
