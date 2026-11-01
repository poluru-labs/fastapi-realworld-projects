from pydantic import BaseModel, ConfigDict, Field


class EvaluateContext(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(min_length=1, max_length=120)
    attributes: dict[str, str] = Field(default_factory=dict)


class EvaluateRequest(BaseModel):
    flag_keys: list[str] = Field(min_length=1, max_length=20)
    context: EvaluateContext


class FlagEvaluation(BaseModel):
    key: str
    enabled: bool
    reason: str


class EvaluateResponse(BaseModel):
    evaluations: list[FlagEvaluation]
