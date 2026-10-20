class LikeRepository:
    """One like per (user_id, post_id)."""

    def __init__(self) -> None:
        self._likes: set[tuple[int, int]] = set()

    def add(self, user_id: int, post_id: int) -> None:
        self._likes.add((user_id, post_id))

    def remove(self, user_id: int, post_id: int) -> None:
        self._likes.discard((user_id, post_id))

    def has_like(self, user_id: int, post_id: int) -> bool:
        return (user_id, post_id) in self._likes

    def count_for_post(self, post_id: int) -> int:
        return sum(1 for _, liked_post in self._likes if liked_post == post_id)

    def delete_for_post(self, post_id: int) -> None:
        self._likes = {(user_id, liked) for user_id, liked in self._likes if liked != post_id}
