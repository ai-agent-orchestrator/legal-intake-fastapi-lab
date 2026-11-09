from dataclasses import asdict
import json

from anyio import from_thread

from app.repositories.intake_repository import IntakeRepository
from app.schemas.intake import IntakeCreateRequest, IntakeResponse
from app.security.context import Envelope, RequestContext, fingerprint
from app.security.session_guard import ContextSessionGuard


class IntakeService:
    def __init__(self, repository: IntakeRepository, guard: ContextSessionGuard):
        self.repository = repository
        self.guard = guard

    def register(self, body: IntakeCreateRequest, session_id: str | None = None) -> IntakeResponse:
        # The def route runs in AnyIO's worker. Execute the shared async rail on
        # its event loop and finish all checks before acquiring the repository lock.
        safe = from_thread.run(self._prepare, body, session_id)
        intake = self.repository.save(safe["client_name"], body.case_type,
                                      safe["core_statement"], safe["desired_next_step"])
        return IntakeResponse(**asdict(intake))

    async def _prepare(self, body: IntakeCreateRequest, session_id: str | None):
        fields = {"client_name": body.client_name, "core_statement": body.core_statement,
                  "desired_next_step": body.desired_next_step}
        text = json.dumps(fields, ensure_ascii=False)
        context = RequestContext.create(session_id, "new-intake:" + fingerprint(text), "intake")
        await self.guard.begin(context, Envelope.bind(context, text))
        # Inspect the combined values too: a directive split over DTO fields
        # must not bypass policy because JSON keys separate its words.
        combined = "\n".join(value for value in fields.values() if value is not None)
        await self.guard.protect_input(context, Envelope.bind(context, combined))
        for name, value in fields.items():
            if value is not None:
                fields[name] = (await self.guard.protect_input(context, Envelope.bind(context, value))).text
        return fields

    def find(self, intake_id: int) -> IntakeResponse:
        fields = asdict(self.repository.find_by_id(intake_id))
        # Also cover snapshots inserted before this masking policy was deployed.
        return IntakeResponse(**from_thread.run(self._publish, fields))

    async def _publish(self, fields: dict):
        text = json.dumps(fields, ensure_ascii=False)
        context = RequestContext.create(None, "intake-read:" + fingerprint(text), "intake")
        for name in ("client_name", "core_statement", "desired_next_step"):
            if fields[name] is not None:
                source = Envelope.bind(context, fields[name])
                safe = await self.guard.mask_stored_output(context, source)
                fields[name] = await self.guard.publish(context, safe)
        return fields
