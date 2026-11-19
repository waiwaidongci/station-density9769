from pydantic import BaseModel, Field


class RetestInput(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    early_run_id: int
    period1_source_id: int
    period2_source_id: int
