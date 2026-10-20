class FollowRepository:
    """Directed follow edges: follower_id follows following_id."""

    def __init__(self) -> None:
        self._edges: set[tuple[int, int]] = set()

    def follow(self, follower_id: int, following_id: int) -> None:
        self._edges.add((follower_id, following_id))

    def unfollow(self, follower_id: int, following_id: int) -> None:
        self._edges.discard((follower_id, following_id))

    def is_following(self, follower_id: int, following_id: int) -> bool:
        return (follower_id, following_id) in self._edges

    def list_followers(self, user_id: int) -> list[int]:
        return sorted(follower for follower, following in self._edges if following == user_id)

    def list_following(self, user_id: int) -> list[int]:
        return sorted(following for follower, following in self._edges if follower == user_id)

    def follower_count(self, user_id: int) -> int:
        return len(self.list_followers(user_id))

    def following_count(self, user_id: int) -> int:
        return len(self.list_following(user_id))
