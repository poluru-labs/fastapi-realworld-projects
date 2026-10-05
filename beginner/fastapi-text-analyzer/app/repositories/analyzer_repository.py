_STOP_WORDS: tuple[str, ...] = (
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "but",
    "by",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "his",
    "i",
    "if",
    "in",
    "is",
    "it",
    "its",
    "my",
    "no",
    "not",
    "of",
    "on",
    "or",
    "our",
    "she",
    "that",
    "the",
    "their",
    "them",
    "they",
    "this",
    "to",
    "was",
    "we",
    "were",
    "with",
    "you",
    "your",
)

if len(set(_STOP_WORDS)) != len(_STOP_WORDS):
    raise RuntimeError("Duplicate entry in the stop-word catalog")

_STOP_WORD_SET = frozenset(_STOP_WORDS)


class AnalyzerRepository:
    """Read-only catalog of English stop words used by word ranking."""

    def list_stop_words(self) -> list[str]:
        return list(_STOP_WORDS)

    def is_stop_word(self, word: str) -> bool:
        return word in _STOP_WORD_SET
