from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ScenarioManager:
    """
    Manages the current state of training scenarios.

    This first version stores scenarios in application memory.
    Restarting FastAPI will clear the scenarios.

    Later, scenario state can be moved into SQLite without changing
    the rest of the application very much.
    """

    def __init__(self) -> None:
        self._scenarios: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    @staticmethod
    def _utc_timestamp() -> str:
        """
        Return a timezone-aware UTC timestamp.

        Example:
        2026-07-21T16:25:41.123456+00:00
        """
        return datetime.now(timezone.utc).isoformat()

    def _create_timeline_event(
        self,
        event_type: str,
        title: str,
        message: str,
        severity: str = "Info",
        progress: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a consistent timeline event structure.

        Every timeline event uses the same fields so that the React
        timeline can render all events predictably.
        """
        return {
            "id": str(uuid4()),
            "timestamp": self._utc_timestamp(),
            "event_type": event_type,
            "title": title,
            "message": message,
            "severity": severity,
            "progress": progress,
            "metadata": metadata or {},
        }

    def create_scenario(
        self,
        attack_id: str,
        attack_name: str,
        target_ids: List[int],
        notes: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new scenario and store it in memory.
        """
        scenario_id = str(uuid4())
        created_at = self._utc_timestamp()

        scenario = {
            "id": scenario_id,
            "attack_id": attack_id,
            "attack_name": attack_name,
            "target_ids": target_ids,
            "notes": notes,
            "created_by": created_by,
            "status": "Pending",
            "progress": 0,
            "current_step": None,
            "created_at": created_at,
            "started_at": None,
            "completed_at": None,
            "updated_at": created_at,
            "timeline": [],
        }

        scenario["timeline"].append(
            self._create_timeline_event(
                event_type="scenario_created",
                title="Scenario Created",
                message=f'Training scenario "{attack_name}" was created.',
                severity="Info",
                progress=0,
                metadata={
                    "attack_id": attack_id,
                    "target_ids": target_ids,
                },
            )
        )

        with self._lock:
            self._scenarios[scenario_id] = scenario

        return deepcopy(scenario)

    def list_scenarios(self) -> List[Dict[str, Any]]:
        """
        Return all scenarios, newest first.
        """
        with self._lock:
            scenarios = list(self._scenarios.values())

        ordered_scenarios = sorted(
            scenarios,
            key=lambda scenario: scenario["created_at"],
            reverse=True,
        )

        return deepcopy(ordered_scenarios)

    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """
        Return one scenario or None when it does not exist.
        """
        with self._lock:
            scenario = self._scenarios.get(scenario_id)

        if scenario is None:
            return None

        return deepcopy(scenario)

    def start_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """
        Mark a pending scenario as running.
        """
        with self._lock:
            scenario = self._scenarios.get(scenario_id)

            if scenario is None:
                return None

            if scenario["status"] == "Running":
                return deepcopy(scenario)

            timestamp = self._utc_timestamp()

            scenario["status"] = "Running"
            scenario["progress"] = max(scenario["progress"], 1)
            scenario["started_at"] = scenario["started_at"] or timestamp
            scenario["updated_at"] = timestamp

            scenario["timeline"].append(
                self._create_timeline_event(
                    event_type="scenario_started",
                    title="Scenario Started",
                    message=(
                        f'The "{scenario["attack_name"]}" exercise started.'
                    ),
                    severity="Info",
                    progress=scenario["progress"],
                )
            )

            return deepcopy(scenario)

    def update_progress(
        self,
        scenario_id: str,
        progress: int,
        current_step: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update scenario progress and the current execution step.

        Progress is restricted to a value between 0 and 100.
        """
        safe_progress = max(0, min(100, progress))

        with self._lock:
            scenario = self._scenarios.get(scenario_id)

            if scenario is None:
                return None

            scenario["progress"] = safe_progress
            scenario["current_step"] = current_step
            scenario["updated_at"] = self._utc_timestamp()

            return deepcopy(scenario)

    def add_timeline_event(
        self,
        scenario_id: str,
        event_type: str,
        title: str,
        message: str,
        severity: str = "Info",
        progress: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Add an event to a scenario timeline.
        """
        with self._lock:
            scenario = self._scenarios.get(scenario_id)

            if scenario is None:
                return None

            event = self._create_timeline_event(
                event_type=event_type,
                title=title,
                message=message,
                severity=severity,
                progress=progress,
                metadata=metadata,
            )

            scenario["timeline"].append(event)
            scenario["updated_at"] = self._utc_timestamp()

            if progress is not None:
                scenario["progress"] = max(0, min(100, progress))

            return deepcopy(event)

    def complete_scenario(
        self,
        scenario_id: str,
        message: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Mark a scenario as completed.
        """
        with self._lock:
            scenario = self._scenarios.get(scenario_id)

            if scenario is None:
                return None

            timestamp = self._utc_timestamp()

            scenario["status"] = "Completed"
            scenario["progress"] = 100
            scenario["current_step"] = None
            scenario["completed_at"] = timestamp
            scenario["updated_at"] = timestamp

            scenario["timeline"].append(
                self._create_timeline_event(
                    event_type="scenario_completed",
                    title="Scenario Completed",
                    message=message
                    or (
                        f'The "{scenario["attack_name"]}" exercise completed.'
                    ),
                    severity="Info",
                    progress=100,
                )
            )

            return deepcopy(scenario)

    def fail_scenario(
        self,
        scenario_id: str,
        message: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Mark a scenario as failed.
        """
        with self._lock:
            scenario = self._scenarios.get(scenario_id)

            if scenario is None:
                return None

            timestamp = self._utc_timestamp()

            scenario["status"] = "Failed"
            scenario["current_step"] = None
            scenario["updated_at"] = timestamp

            scenario["timeline"].append(
                self._create_timeline_event(
                    event_type="scenario_failed",
                    title="Scenario Failed",
                    message=message,
                    severity="Critical",
                    progress=scenario["progress"],
                )
            )

            return deepcopy(scenario)


scenario_manager = ScenarioManager()