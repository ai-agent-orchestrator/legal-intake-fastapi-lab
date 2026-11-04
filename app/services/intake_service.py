from dataclasses import asdict

from app.repositories.intake_repository import IntakeRepository
from app.schemas.intake import IntakeCreateRequest, IntakeResponse


class IntakeService:
    def __init__(self, repository: IntakeRepository):
        self.repository = repository

    def register(self, body: IntakeCreateRequest) -> IntakeResponse:
        intake = self.repository.save(body.client_name, body.case_type, body.core_statement, body.desired_next_step)
        return IntakeResponse(**asdict(intake))

    def find(self, intake_id: int) -> IntakeResponse:
        return IntakeResponse(**asdict(self.repository.find_by_id(intake_id)))
