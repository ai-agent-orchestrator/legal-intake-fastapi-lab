from typing import Annotated

from fastapi import Depends, Request

from app.clients.llm_client import LlmClient
from app.repositories.intake_repository import IntakeRepository
from app.services.guidance_service import GuidanceService
from app.services.intake_service import IntakeService


def get_repository(request: Request) -> IntakeRepository:
    return request.app.state.intake_repository


def get_llm_client(request: Request) -> LlmClient:
    return request.app.state.llm_client


RepositoryDep = Annotated[IntakeRepository, Depends(get_repository)]
LlmDep = Annotated[LlmClient, Depends(get_llm_client)]


def get_intake_service(repository: RepositoryDep) -> IntakeService:
    return IntakeService(repository)


def get_guidance_service(repository: RepositoryDep, llm: LlmDep) -> GuidanceService:
    return GuidanceService(repository, llm)


IntakeServiceDep = Annotated[IntakeService, Depends(get_intake_service)]
GuidanceServiceDep = Annotated[GuidanceService, Depends(get_guidance_service)]
