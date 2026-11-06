import logging
from threading import current_thread

from fastapi import APIRouter, Header
from typing import Annotated

from app.dependencies import GuidanceServiceDep, IntakeServiceDep
from app.schemas.intake import GuidanceResponse, IntakeCreateRequest, IntakeResponse

router = APIRouter(prefix="/api/intakes", tags=["Legal Intake MVP"])
logger = logging.getLogger("uvicorn.error")


@router.post("", response_model=IntakeResponse, status_code=201)
def register_intake(body: IntakeCreateRequest, service: IntakeServiceDep) -> IntakeResponse:
    logger.info("[register] thread=%s", current_thread().name)
    return service.register(body)


@router.get("/{intake_id}", response_model=IntakeResponse)
def find_intake(intake_id: int, service: IntakeServiceDep) -> IntakeResponse:
    logger.info("[find] thread=%s intakeId=%s", current_thread().name, intake_id)
    return service.find(intake_id)


@router.post("/{intake_id}/guidance", response_model=GuidanceResponse)
async def create_guidance(intake_id: int, service: GuidanceServiceDep,
    session_id: Annotated[str | None, Header(alias="X-Session-ID", min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")] = None,
) -> GuidanceResponse:
    logger.info("[guidance] thread=%s intakeId=%s", current_thread().name, intake_id)
    return await service.create_guidance(intake_id, session_id)
