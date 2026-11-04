from pydantic import Field, field_validator

from app.domain.intake import CaseType
from app.schemas.base import CamelModel


class IntakeCreateRequest(CamelModel):
    client_name: str = Field(min_length=1, max_length=50)
    case_type: CaseType
    core_statement: str = Field(min_length=1, max_length=100)
    desired_next_step: str | None = Field(default=None, max_length=100)

    @field_validator("desired_next_step")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        return value or None


class IntakeResponse(CamelModel):
    intake_id: int
    client_name: str
    case_type: CaseType
    core_statement: str
    desired_next_step: str | None


class GuidanceResponse(CamelModel):
    intake_id: int
    answer: str
    model: str
