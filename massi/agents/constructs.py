from typing import TypedDict

from pydantic import BaseModel


class ValidationError(TypedDict):
    message: str
    encountered_value: str
    json_path: str
    failed_key: str


type QueryStepId = int
type QueryPrompt = str


class QueryStep(BaseModel):
    id: QueryStepId
    key: str
    json_path: str
    priority: int
    query: QueryPrompt


class QueryPlan(BaseModel):
    queries: dict[QueryStepId, QueryStep]
