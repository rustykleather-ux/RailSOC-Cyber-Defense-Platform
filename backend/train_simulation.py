import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import SessionLocal
from models import OTDevice, TrackBlock, Train, TrainHistory


class TrainSimulationEngine:
    """
    Database-backed train simulation engine for TrackSentinel.

    Responsibilities:
    - Move active trains across the configured milepost territory.
    - Record train history after each simulation tick.
    - Update TrackBlock occupancy.
    - Update block signal aspects.
    - Update controlling OT device status.
    - Support start, stop, restart, reset, tick, and status operations.
    """

    ACTIVE_TRAIN_STATUSES = {"Moving", "Restricted"}

    def __init__(
        self,
        interval_seconds: int = 3,
        minimum_milepost: float = 80.0,
        maximum_milepost: float = 100.0,
    ):
        self.interval_seconds = interval_seconds
        self.minimum_milepost = minimum_milepost
        self.maximum_milepost = maximum_milepost

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self.track_events: List[Dict[str, Any]] = [
            {
                "name": "Signal Controller 14A",
                "milepost": 80.0,
                "type": "signal",
            },
            {
                "name": "Grade Crossing Controller MP 82.4",
                "milepost": 82.4,
                "type": "crossing",
            },
            {
                "name": "Signal Controller 14B",
                "milepost": 87.1,
                "type": "signal",
            },
            {
                "name": "Hot Bearing Detector",
                "milepost": 95.2,
                "type": "detector",
            },
        ]

    # =====================================================
    # Engine lifecycle
    # =====================================================

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def start(self) -> bool:
        """
        Start the background simulation thread.

        Returns:
            True if the simulation started.
            False if it was already running.
        """
        with self._lock:
            if self._running:
                return False

            self._running = True

            self._thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
                name="TrackSentinelTrainSimulation",
            )

            self._thread.start()

        print("[TRAIN SIMULATION] Started.")
        return True

    def stop(self) -> bool:
        """
        Stop the background simulation thread.

        Returns:
            True if a running simulation was stopped.
            False if the simulation was already stopped.
        """
        with self._lock:
            if not self._running:
                return False

            self._running = False
            thread = self._thread

        if (
            thread
            and thread.is_alive()
            and thread is not threading.current_thread()
        ):
            thread.join(timeout=self.interval_seconds + 2)

        with self._lock:
            self._thread = None

        print("[TRAIN SIMULATION] Stopped.")
        return True

    def restart(self, reset: bool = True) -> Dict[str, Any]:
        """
        Stop, optionally reset, and restart the simulation.
        """
        was_running = self.is_running

        if was_running:
            self.stop()

        if reset:
            self.reset_trains()

        started = self.start()

        return {
            "success": started,
            "running": self.is_running,
            "reset_performed": reset,
            "message": (
                "Train simulation restarted."
                if started
                else "Train simulation could not be restarted."
            ),
        }

    def get_status(self) -> Dict[str, Any]:
        """
        Return the current engine status.
        """
        thread_alive = bool(
            self._thread and self._thread.is_alive()
        )

        return {
            "running": self.is_running,
            "thread_alive": thread_alive,
            "interval_seconds": self.interval_seconds,
            "minimum_milepost": self.minimum_milepost,
            "maximum_milepost": self.maximum_milepost,
        }

    def _run_loop(self) -> None:
        """
        Execute simulation ticks until the engine is stopped.
        """
        while self.is_running:
            started_at = time.monotonic()

            try:
                self.tick()
            except Exception as exc:
                print(
                    "[TRAIN SIMULATION ERROR] "
                    f"{type(exc).__name__}: {exc}"
                )

            elapsed = time.monotonic() - started_at
            sleep_time = max(
                0.0,
                self.interval_seconds - elapsed,
            )

            time.sleep(sleep_time)

        print("[TRAIN SIMULATION] Background loop exited.")

    # =====================================================
    # Simulation tick
    # =====================================================

    def tick(self) -> Dict[str, Any]:
        """
        Run one simulation cycle.
        """
        db = SessionLocal()

        try:
            trains = (
                db.query(Train)
                .order_by(Train.id)
                .all()
            )

            for train in trains:
                self._update_train(train, db)

            self.update_block_occupancy(db)
            self.update_signal_states(db)

            db.commit()

            return {
                "success": True,
                "trains_processed": len(trains),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

    # =====================================================
    # Train movement
    # =====================================================

    def _update_train(
        self,
        train: Train,
        db,
    ) -> None:
        """
        Update one train for a simulation tick.
        """
        status = (train.status or "").strip()

        if status not in self.ACTIVE_TRAIN_STATUSES:
            self._record_history(train, db)
            return

        if train.speed is None or float(train.speed) <= 0:
            train.speed = 0
            train.status = "Stopped"
            train.current_signal = "Stop"
            train.last_updated = datetime.utcnow()

            self._record_history(train, db)
            return

        previous_milepost = float(
            train.milepost
            if train.milepost is not None
            else self.minimum_milepost
        )

        milepost_change = self._calculate_milepost_change(
            float(train.speed)
        )

        direction = (
            train.direction or "Eastbound"
        ).strip().lower()

        if direction == "westbound":
            next_milepost = (
                previous_milepost - milepost_change
            )
        else:
            next_milepost = (
                previous_milepost + milepost_change
            )

        if next_milepost >= self.maximum_milepost:
            train.milepost = self.maximum_milepost
            train.speed = 0
            train.status = "Arrived"
            train.current_signal = "Stop"

        elif next_milepost <= self.minimum_milepost:
            train.milepost = self.minimum_milepost
            train.speed = 0
            train.status = "Arrived"
            train.current_signal = "Stop"

        else:
            train.milepost = round(next_milepost, 3)
            train.current_signal = (
                self._calculate_signal_state(train)
            )

        train.last_updated = datetime.utcnow()

        crossed_events = self._get_crossed_track_events(
            previous_milepost=previous_milepost,
            current_milepost=float(train.milepost),
            direction=direction,
        )

        for event in crossed_events:
            self._process_track_event(
                train=train,
                event=event,
            )

        self._record_history(train, db)

    def _calculate_milepost_change(
        self,
        speed_mph: float,
    ) -> float:
        """
        Convert train speed into milepost movement per tick.
        """
        hours_per_tick = (
            self.interval_seconds / 3600.0
        )

        return float(speed_mph) * hours_per_tick

    def _calculate_signal_state(
        self,
        train: Train,
    ) -> str:
        """
        Determine the train's current displayed signal state.
        """
        if train.status == "Restricted":
            return "Approach"

        if not train.ptc_enabled:
            return "Restricted"

        if train.speed is None or float(train.speed) <= 0:
            return "Stop"

        if float(train.speed) <= 25:
            return "Approach"

        return "Clear"

    # =====================================================
    # Track block occupancy
    # =====================================================

    def update_block_occupancy(
        self,
        db,
    ) -> None:
        """
        Clear and recalculate block occupancy using database TrackBlock rows.
        """
        trains = (
            db.query(Train)
            .order_by(Train.id)
            .all()
        )

        blocks = (
            db.query(TrackBlock)
            .order_by(TrackBlock.start_milepost)
            .all()
        )

        now = datetime.utcnow()

        for block in blocks:
            block.occupied = False
            block.occupied_train_id = None
            block.last_updated = now

        for train in trains:
            if train.milepost is None:
                continue

            milepost = float(train.milepost)

            for index, block in enumerate(blocks):
                start_milepost = float(
                    block.start_milepost
                )
                end_milepost = float(
                    block.end_milepost
                )

                is_last_block = (
                    index == len(blocks) - 1
                )

                if is_last_block:
                    inside_block = (
                        start_milepost
                        <= milepost
                        <= end_milepost
                    )
                else:
                    inside_block = (
                        start_milepost
                        <= milepost
                        < end_milepost
                    )

                if inside_block:
                    block.occupied = True
                    block.occupied_train_id = train.id
                    block.last_updated = now
                    break

    # =====================================================
    # Signal state updates
    # =====================================================

    def update_signal_states(
        self,
        db,
    ) -> None:
        """
        Calculate each TrackBlock signal indication.
        """
        blocks = (
            db.query(TrackBlock)
            .order_by(TrackBlock.start_milepost)
            .all()
        )

        now = datetime.utcnow()

        for index, block in enumerate(blocks):
            next_block = (
                blocks[index + 1]
                if index + 1 < len(blocks)
                else None
            )

            communications_status = (
                block.communications_status or "Online"
            ).strip().lower()

            if communications_status != "online":
                indication = "Dark"

            elif bool(block.maintenance):
                indication = "Stop"

            elif bool(block.occupied):
                indication = "Stop"

            elif next_block and bool(next_block.occupied):
                indication = "Approach"

            else:
                indication = "Clear"

            block.signal_aspect = indication
            block.last_updated = now

            self._update_controlling_device(
                block=block,
                indication=indication,
                db=db,
                timestamp=now,
            )

            print(
                "[BLOCK SIGNAL] "
                f"{block.name}: {indication}"
            )

    def _update_controlling_device(
        self,
        block: TrackBlock,
        indication: str,
        db,
        timestamp: datetime,
    ) -> None:
        """
        Update the OT device associated with a track block.
        """
        if not block.controlling_device_id:
            return

        signal_device = (
            db.query(OTDevice)
            .filter(
                OTDevice.id
                == block.controlling_device_id
            )
            .first()
        )

        if not signal_device:
            return

        if indication == "Dark":
            signal_device.status = "Degraded"
        else:
            signal_device.status = "Online"

        signal_device.last_seen = timestamp

    # =====================================================
    # Track events
    # =====================================================

    def _get_crossed_track_events(
        self,
        previous_milepost: float,
        current_milepost: float,
        direction: str,
    ) -> List[Dict[str, Any]]:
        normalized_direction = (
            direction or "eastbound"
        ).strip().lower()

        if normalized_direction == "westbound":
            crossed_events = [
                event
                for event in self.track_events
                if (
                    current_milepost
                    <= float(event["milepost"])
                    < previous_milepost
                )
            ]

            return sorted(
                crossed_events,
                key=lambda event: float(
                    event["milepost"]
                ),
                reverse=True,
            )

        crossed_events = [
            event
            for event in self.track_events
            if (
                previous_milepost
                < float(event["milepost"])
                <= current_milepost
            )
        ]

        return sorted(
            crossed_events,
            key=lambda event: float(
                event["milepost"]
            ),
        )

    def _process_track_event(
        self,
        train: Train,
        event: Dict[str, Any],
    ) -> None:
        event_type = str(
            event.get("type", "")
        ).strip().lower()

        event_name = str(
            event.get("name", "Unknown Track Event")
        )

        event_milepost = float(
            event.get(
                "milepost",
                train.milepost
                or self.minimum_milepost,
            )
        )

        if event_type == "signal":
            self._process_signal_event(
                train=train,
                event_name=event_name,
                event_milepost=event_milepost,
            )

        elif event_type == "crossing":
            self._process_crossing_event(
                train=train,
                event_name=event_name,
                event_milepost=event_milepost,
            )

        elif event_type == "detector":
            self._process_detector_event(
                train=train,
                event_name=event_name,
                event_milepost=event_milepost,
            )

        else:
            print(
                f"[TRACK EVENT] {train.symbol} passed "
                f"{event_name} at MP {event_milepost}"
            )

    def _process_signal_event(
        self,
        train: Train,
        event_name: str,
        event_milepost: float,
    ) -> None:
        train.current_signal = (
            self._calculate_signal_state(train)
        )

        print(
            f"[SIGNAL] {train.symbol} passed "
            f"{event_name} at MP {event_milepost}. "
            f"Signal indication: "
            f"{train.current_signal}"
        )

    def _process_crossing_event(
        self,
        train: Train,
        event_name: str,
        event_milepost: float,
    ) -> None:
        print(
            f"[CROSSING] {train.symbol} entered "
            f"{event_name} at MP {event_milepost}. "
            "Crossing activation sequence triggered."
        )

    def _process_detector_event(
        self,
        train: Train,
        event_name: str,
        event_milepost: float,
    ) -> None:
        print(
            f"[DETECTOR] {train.symbol} passed "
            f"{event_name} at MP {event_milepost}. "
            "Detector inspection completed."
        )

    # =====================================================
    # History
    # =====================================================

    def _record_history(
        self,
        train: Train,
        db,
    ) -> None:
        """
        Store a train-state history row.
        """
        history = TrainHistory(
            train_id=train.id,
            milepost=float(
                train.milepost
                if train.milepost is not None
                else self.minimum_milepost
            ),
            speed=int(train.speed or 0),
            status=train.status,
            current_signal=train.current_signal,
            authority=train.authority,
            ptc_enabled=bool(train.ptc_enabled),
            timestamp=datetime.utcnow(),
        )

        db.add(history)

    # =====================================================
    # Reset
    # =====================================================

    def reset_trains(self) -> Dict[str, Any]:
        """
        Restore trains and track blocks to the operational baseline.
        """
        db = SessionLocal()

        try:
            trains = (
                db.query(Train)
                .order_by(Train.id)
                .all()
            )

            for index, train in enumerate(trains):
                direction = (
                    train.direction or "Eastbound"
                ).strip().lower()

                if direction == "westbound":
                    reset_milepost = (
                        self.maximum_milepost
                        - (index * 0.5)
                    )
                else:
                    reset_milepost = (
                        self.minimum_milepost
                        + (index * 0.5)
                    )

                reset_milepost = max(
                    self.minimum_milepost,
                    min(
                        self.maximum_milepost,
                        reset_milepost,
                    ),
                )

                train.milepost = round(
                    reset_milepost,
                    3,
                )
                train.speed = 40
                train.status = "Moving"
                train.ptc_enabled = True
                train.authority = "Main Track"
                train.current_signal = "Clear"
                train.last_updated = datetime.utcnow()

            db.query(TrainHistory).delete(
                synchronize_session=False
            )

            self.update_block_occupancy(db)
            self.update_signal_states(db)

            db.commit()

            print(
                "[TRAIN SIMULATION] "
                "Operational baseline restored."
            )

            return {
                "success": True,
                "trains_reset": len(trains),
                "message": (
                    "Train simulation baseline restored."
                ),
            }

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()


train_simulation = TrainSimulationEngine(
    interval_seconds=3,
    minimum_milepost=80.0,
    maximum_milepost=100.0,
)