"""TASK-083 Windows composition boundary with no native resource effects.

This is intentionally not a Windows resource probe or reservation backend.
Until the TASK-046 H3 V2 compound authorization and TASK-066 workload mapping
exist, it exposes only the current body-free production admission result and
rejects every effectful entrypoint before it can receive host data.
"""

from __future__ import annotations

from typing import Any, Mapping

from .task083_voice_training_resource_reservation import (
    Task083ProductionReservationAdmissionV1,
    Task083ResourceReservationPlanV1,
    compile_production_reservation_admission,
)


class Task083WindowsResourceEffectBlocked(RuntimeError):
    """Raised before any Windows resource or training side effect."""


class Task083WindowsReservationBackend:
    """Sealed effect-zero boundary for a future trusted Windows backend."""

    __slots__ = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("Task083WindowsReservationBackend cannot be subclassed")

    @property
    def resource_effect_count(self) -> int:
        """No native observation, reservation, or process action is performed."""

        return 0

    def compile_production_admission(
        self,
        plan: Mapping[str, Any] | Task083ResourceReservationPlanV1,
        *,
        evaluated_at: str,
    ) -> Task083ProductionReservationAdmissionV1:
        """Return the current fail-closed, effect-zero production admission."""

        return compile_production_reservation_admission(plan, evaluated_at=evaluated_at)

    def observe_native_resources(self) -> None:
        """Refuse native probing before a host observation can be attempted."""

        raise Task083WindowsResourceEffectBlocked(
            "TASK-083 native resource observation requires H3 TRAINING_START"
        )

    def reserve_native_resources(self) -> None:
        """Refuse CPU/GPU/RAM/VRAM/disk reservation before any host effect."""

        raise Task083WindowsResourceEffectBlocked(
            "TASK-083 native resource reservation requires H3 TRAINING_START"
        )

    def start_training_process(self) -> None:
        """Refuse process dispatch; this boundary has no training authority."""

        raise Task083WindowsResourceEffectBlocked(
            "TASK-083 training dispatch requires TASK-046 compound authorization"
        )


def open_task083_windows_reservation_backend() -> Task083WindowsReservationBackend:
    """Create the inert, trusted-composition boundary without host inputs."""

    return Task083WindowsReservationBackend()
