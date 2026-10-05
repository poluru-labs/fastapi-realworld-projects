from typing import Annotated

from fastapi import APIRouter, Body, Depends

from app.api.deps import get_text_service
from app.schemas.text import AnalyzeRead, AnalyzeRequest
from app.services.text_service import TextService

router = APIRouter()

_EXAMPLES = {
    "greeting": {
        "summary": "Repeated greeting",
        "description": "Two sentences. 'hello' should rank above 'world'.",
        "value": {
            "text": "Hello, world! Hello.",
            "top_n": 5,
            "ignore_stop_words": False,
        },
    },
    "palindrome": {
        "summary": "Classic palindrome",
        "description": "Punctuation and spaces are ignored for the palindrome check.",
        "value": {
            "text": "A man, a plan, a canal: Panama",
            "top_n": 5,
            "ignore_stop_words": False,
        },
    },
    "skip_stop_words": {
        "summary": "Rank content words only",
        "description": "'the' and 'and' drop out of top_words. The word count still includes them.",
        "value": {
            "text": "The cat and the dog",
            "top_n": 5,
            "ignore_stop_words": True,
        },
    },
}


@router.post(
    "",
    response_model=AnalyzeRead,
    summary="Analyze a piece of text",
    response_description="Counts, reading time, palindrome flag, and ranked words",
    description=(
        "Counts characters, words, sentences, and paragraphs. "
        "A word is a run of ASCII letters or digits, with an optional apostrophe "
        "(`don't`). Sentences split on `.`, `!`, and `?`. "
        "Paragraphs split on a blank line. "
        "Nothing is stored; each call is independent."
    ),
    responses={
        422: {"description": "Text is blank, too long, or top_n is outside 1–50."},
    },
)
def analyze_text(
    payload: Annotated[AnalyzeRequest, Body(openapi_examples=_EXAMPLES)],
    service: Annotated[TextService, Depends(get_text_service)],
) -> AnalyzeRead:
    return service.analyze(payload)
