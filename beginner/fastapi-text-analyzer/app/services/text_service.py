import re
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal

from app.core.constants import (
    MAX_TEXT_LENGTH,
    MAX_TOP_N,
    READING_WORDS_PER_MINUTE,
)
from app.repositories.analyzer_repository import AnalyzerRepository
from app.schemas.text import (
    AnalyzeRead,
    AnalyzeRequest,
    AnalyzerOptionsRead,
    TransformMode,
    TransformRead,
    TransformRequest,
    WordCount,
)

_WORD = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")
_SENTENCE_SPLIT = re.compile(r"[.!?]+")
_NON_ALNUM = re.compile(r"[^A-Za-z0-9]+")


def _round_half_up(value: Decimal, places: str) -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _words(text: str) -> list[str]:
    return [match.group(0).lower() for match in _WORD.finditer(text)]


def _sentences(text: str) -> int:
    return sum(1 for part in _SENTENCE_SPLIT.split(text) if _WORD.search(part))


def _paragraphs(text: str) -> int:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return 0
    return sum(1 for part in re.split(r"\n\s*\n", normalized) if part.strip())


def _average_word_length(words: list[str]) -> float:
    if not words:
        return 0.0
    total = sum(len(word) for word in words)
    averaged = _round_half_up(Decimal(total) / Decimal(len(words)), "0.01")
    return float(averaged)


def _reading_seconds(word_count: int) -> int:
    if word_count == 0:
        return 0
    seconds = Decimal(word_count) * Decimal(60) / Decimal(READING_WORDS_PER_MINUTE)
    return int(_round_half_up(seconds, "1"))


def _is_palindrome(text: str) -> bool:
    letters = _NON_ALNUM.sub("", text).lower()
    return bool(letters) and letters == letters[::-1]


def _title_case(text: str) -> str:
    return _WORD.sub(lambda match: match.group(0).capitalize(), text)


def _slug(text: str) -> str:
    return _NON_ALNUM.sub("-", text.lower()).strip("-")


class TextService:
    def __init__(self, repository: AnalyzerRepository) -> None:
        self._repo = repository

    def list_options(self) -> AnalyzerOptionsRead:
        stop_words = self._repo.list_stop_words()
        return AnalyzerOptionsRead(
            reading_words_per_minute=READING_WORDS_PER_MINUTE,
            max_text_length=MAX_TEXT_LENGTH,
            max_top_n=MAX_TOP_N,
            transform_modes=list(TransformMode),
            stop_word_count=len(stop_words),
            stop_words=stop_words,
        )

    def analyze(self, payload: AnalyzeRequest) -> AnalyzeRead:
        words = _words(payload.text)
        ranked = words
        if payload.ignore_stop_words:
            ranked = [word for word in words if not self._repo.is_stop_word(word)]
        top = sorted(Counter(ranked).items(), key=lambda item: (-item[1], item[0]))
        return AnalyzeRead(
            characters=len(payload.text),
            characters_no_spaces=sum(1 for char in payload.text if not char.isspace()),
            words=len(words),
            unique_words=len(set(words)),
            sentences=_sentences(payload.text),
            paragraphs=_paragraphs(payload.text),
            average_word_length=_average_word_length(words),
            reading_time_seconds=_reading_seconds(len(words)),
            is_palindrome=_is_palindrome(payload.text),
            top_words=[WordCount(word=word, count=count) for word, count in top[: payload.top_n]],
        )

    def transform(self, payload: TransformRequest) -> TransformRead:
        match payload.mode:
            case TransformMode.lower:
                result = payload.text.lower()
            case TransformMode.upper:
                result = payload.text.upper()
            case TransformMode.title:
                result = _title_case(payload.text)
            case TransformMode.reverse:
                result = payload.text[::-1]
            case TransformMode.slug:
                result = _slug(payload.text)
        return TransformRead(mode=payload.mode, original=payload.text, result=result)
