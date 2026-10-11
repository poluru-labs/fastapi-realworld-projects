from app.schemas.movie import MovieCreate, MovieRead, MovieUpdate, WatchStatus, _normalize_imdb_id

_SEED: dict[int, MovieRead] = {
    1: MovieRead(
        id=1,
        title="Inception",
        director="Christopher Nolan",
        imdb_id="tt1375666",
        genre="Science Fiction",
        release_year=2010,
        runtime_minutes=148,
        status=WatchStatus.WATCHING,
        pinned=True,
    ),
    2: MovieRead(
        id=2,
        title="The Shawshank Redemption",
        director="Frank Darabont",
        imdb_id="tt0111161",
        genre="Drama",
        release_year=1994,
        runtime_minutes=142,
        status=WatchStatus.WANT_TO_WATCH,
        pinned=False,
    ),
    3: MovieRead(
        id=3,
        title="Spirited Away",
        director="Hayao Miyazaki",
        imdb_id=None,
        genre="Animation",
        release_year=2001,
        runtime_minutes=125,
        status=WatchStatus.WATCHED,
        pinned=False,
    ),
}


class MovieRepository:
    """In-memory watchlist. Restarting the process restores the seed movies."""

    def __init__(self) -> None:
        self._movies = dict(_SEED)
        self._next_id = max(self._movies.keys(), default=0) + 1

    def list_movies(
        self,
        *,
        genre: str | None = None,
        search: str | None = None,
        status: WatchStatus | None = None,
        pinned: bool | None = None,
    ) -> list[MovieRead]:
        items = list(self._movies.values())
        if genre is not None:
            needle = genre.strip().casefold()
            if needle:
                items = [movie for movie in items if movie.genre.casefold() == needle]
        if status is not None:
            items = [movie for movie in items if movie.status is status]
        if pinned is not None:
            items = [movie for movie in items if movie.pinned is pinned]
        if search is not None:
            needle = search.strip().casefold()
            if needle:
                items = [
                    movie
                    for movie in items
                    if needle in movie.title.casefold()
                    or needle in movie.director.casefold()
                    or (
                        movie.imdb_id is not None
                        and needle in _normalize_imdb_id(movie.imdb_id)
                    )
                ]
        return sorted(items, key=lambda movie: (not movie.pinned, movie.id))

    def list_genres(self) -> list[str]:
        genres = {movie.genre for movie in self._movies.values()}
        return sorted(genres, key=str.casefold)

    def get(self, movie_id: int) -> MovieRead | None:
        return self._movies.get(movie_id)

    def imdb_id_taken(self, imdb_id: str, *, except_id: int | None = None) -> bool:
        normalized = _normalize_imdb_id(imdb_id)
        for movie in self._movies.values():
            if except_id is not None and movie.id == except_id:
                continue
            if movie.imdb_id is not None and _normalize_imdb_id(movie.imdb_id) == normalized:
                return True
        return False

    def create(self, payload: MovieCreate) -> MovieRead:
        movie = MovieRead(
            id=self._next_id,
            title=payload.title,
            director=payload.director,
            imdb_id=payload.imdb_id,
            genre=payload.genre,
            release_year=payload.release_year,
            runtime_minutes=payload.runtime_minutes,
            status=payload.status,
            pinned=payload.pinned,
        )
        self._movies[self._next_id] = movie
        self._next_id += 1
        return movie

    def replace(self, movie_id: int, payload: MovieCreate) -> MovieRead | None:
        if movie_id not in self._movies:
            return None
        movie = MovieRead(id=movie_id, **payload.model_dump())
        self._movies[movie_id] = movie
        return movie

    def update(self, movie_id: int, payload: MovieUpdate) -> MovieRead | None:
        existing = self._movies.get(movie_id)
        if existing is None:
            return None
        data = existing.model_dump()
        changes = payload.model_dump(exclude_unset=True)
        if "imdb_id" in changes:
            imdb_value = changes["imdb_id"]
            data["imdb_id"] = None if imdb_value is None else imdb_value
            del changes["imdb_id"]
        data.update(changes)
        movie = MovieRead(**data)
        self._movies[movie_id] = movie
        return movie

    def set_pinned(self, movie_id: int, pinned: bool) -> MovieRead | None:
        existing = self._movies.get(movie_id)
        if existing is None:
            return None
        movie = existing.model_copy(update={"pinned": pinned})
        self._movies[movie_id] = movie
        return movie

    def set_status(self, movie_id: int, status: WatchStatus) -> MovieRead | None:
        existing = self._movies.get(movie_id)
        if existing is None:
            return None
        movie = existing.model_copy(update={"status": status})
        self._movies[movie_id] = movie
        return movie

    def delete(self, movie_id: int) -> MovieRead | None:
        return self._movies.pop(movie_id, None)
