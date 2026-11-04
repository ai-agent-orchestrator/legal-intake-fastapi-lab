from threading import Lock

from app.core.exceptions import IntakeNotFoundError
from app.domain.intake import CaseType, Intake


class IntakeRepository:
    """단일 프로세스 학습용 딕셔너리. 서버 재시작 시 초기화된다."""
    def __init__(self):
        self._items: dict[int, Intake] = {}
        self._next_id = 1
        self._lock = Lock()

    def save(self, client_name: str, case_type: CaseType, core_statement: str,
             desired_next_step: str | None) -> Intake:
        with self._lock:
            intake = Intake(self._next_id, client_name, case_type, core_statement, desired_next_step)
            self._items[intake.intake_id] = intake
            self._next_id += 1
            return intake

    def find_by_id(self, intake_id: int) -> Intake:
        with self._lock:
            intake = self._items.get(intake_id)
        if intake is None:
            raise IntakeNotFoundError(intake_id)
        return intake
