from dataclasses import dataclass
from enum import StrEnum


class CaseType(StrEnum):
    CIVIL = "CIVIL"
    CRIMINAL = "CRIMINAL"
    FAMILY = "FAMILY"
    OTHER = "OTHER"


@dataclass(frozen=True)
class Intake:
    intake_id: int
    client_name: str
    case_type: CaseType
    core_statement: str
    desired_next_step: str | None
