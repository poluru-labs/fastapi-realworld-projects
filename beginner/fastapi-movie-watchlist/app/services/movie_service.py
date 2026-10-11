from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.movie_repository import MovieRepository
from app.schemas.movie import MovieCreate, MovieRead, MovieUpdate, WatchStatus


class MovieService:
    def __init__(self, repository: MovieRepository) -> None:
        self._repo = repository

    def list_movies(
        self,
        *,
        genre: str | None = None,
        search: str | None = None,
        status: WatchStatus | None = None,
        pinned: bool | None = None,
    ) -> list[MovieRead]:
        return self._repo.list_movies(
            genre=genre,
            search=search,
            status=status,
            pinned=pinned,
        )

    def list_genres(self) -> list[str]:
        return self._repo.list_genres()

    def get_movie(self, movie_id: int) -> MovieRead:
        movie = self._repo.get(movie_id)
        if movie is None:
            raise NotFoundError("Movie", movie_id)
        return movie

    def create_movie(self, payload: MovieCreate) -> MovieRead:
        if payload.imdb_id is not None and self._repo.imdb_id_taken(payload.imdb_id):
            raise ConflictError("Another movie already uses this IMDb id")
        return self._repo.create(payload)

    def replace_movie(self, movie_id: int, payload: MovieCreate) -> MovieRead:
        if payload.imdb_id is not None and self._repo.imdb_id_taken(
            payload.imdb_id, except_id=movie_id
        ):
            raise ConflictError("Another movie already uses this IMDb id")
        movie = self._repo.replace(movie_id, payload)
        if movie is None:
            raise NotFoundError("Movie", movie_id)
        return movie

    def update_movie(self, movie_id: int, payload: MovieUpdate) -> MovieRead:
        changes = payload.model_dump(exclude_unset=True)
        if "imdb_id" in changes and changes["imdb_id"] not in (None, ""):
            imdb_id = str(changes["imdb_id"])
            if self._repo.imdb_id_taken(imdb_id, except_id=movie_id):
                raise ConflictError("Another movie already uses this IMDb id")
        movie = self._repo.update(movie_id, payload)
        if movie is None:
            raise NotFoundError("Movie", movie_id)
        return movie

    def pin_movie(self, movie_id: int) -> MovieRead:
        movie = self._repo.set_pinned(movie_id, True)
        if movie is None:
            raise NotFoundError("Movie", movie_id)
        return movie

    def unpin_movie(self, movie_id: int) -> MovieRead:
        movie = self._repo.set_pinned(movie_id, False)
        if movie is None:
            raise NotFoundError("Movie", movie_id)
        return movie

    def mark_watched(self, movie_id: int) -> MovieRead:
        movie = self._repo.set_status(movie_id, WatchStatus.WATCHED)
        if movie is None:
            raise NotFoundError("Movie", movie_id)
        return movie

    def delete_movie(self, movie_id: int) -> MovieRead:
        movie = self._repo.delete(movie_id)
        if movie is None:
            raise NotFoundError("Movie", movie_id)
        return movie
