import threading
import time
from datetime import datetime, timezone
from math import sqrt
from typing import Any, Dict, List, Optional

from database import SessionLocal
from models import (
    OTDevice,
    OperationalRestriction,
    TrackBlock,
    TrackSwitch,
    Train,
    TrainHistory,
)
from services.timeline_service import record_event
from services.dispatch_service import process_dispatch_commands, release_cleared_routes


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

    ACTIVE_TRAIN_STATUSES = {
        "Moving",
        "Restricted",
        "Braking for Signal",
        "Stopped at Signal",
        "Stopped at Unsafe Switch",
        "Restricted - PTC Communications",
    }
    NORMAL_SPEED_MPH = 40
    APPROACH_SPEED_MPH = 25
    RESTRICTED_SPEED_MPH = 15
    NORMAL_ACCELERATION_MPH_PER_SECOND = 1.0
    SERVICE_BRAKING_MPH_PER_SECOND = 2.0
    EMERGENCY_BRAKING_MPH_PER_SECOND = 5.0
    SIGNAL_STOP_MARGIN_MILES = 0.01

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
            process_dispatch_commands(db)
            release_cleared_routes(db)

            db.commit()

            return {
                "success": True,
                "trains_processed": len(trains),
                "timestamp": datetime.now(timezone.utc).isoformat(),
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
        restrictions = db.query(OperationalRestriction).filter(
            OperationalRestriction.active.is_(True),
            OperationalRestriction.target_type == "TRAIN",
            OperationalRestriction.target_id == train.id,
        ).all()
        if any(item.restriction_type == "HOLD_TRAIN" for item in restrictions):
            train.status = "Held by Dispatcher"
            train.speed = 0
            train.last_updated = datetime.now(timezone.utc)
            self._record_history(train, db)
            return
        observed_block = self._get_observed_block(train, db)
        unsafe_switch = self._get_unsafe_switch_ahead(train, db)
        observed_target = observed_block
        if unsafe_switch and (
            observed_block is None
            or self._distance_to_target(train, unsafe_switch)
            <= self._distance_to_target(train, observed_block)
        ):
            observed_target = unsafe_switch
        observed_aspect = (
            (observed_block.signal_aspect or "Clear").strip().title()
            if observed_block
            else "Clear"
        )
        if unsafe_switch and observed_target is unsafe_switch:
            observed_aspect = "Stop"
        if (
            observed_block
            and observed_block.occupied
            and observed_block.occupied_train_id not in {None, train.id}
        ):
            observed_aspect = "Stop"
        previous_status = status
        previous_speed = max(float(train.speed or 0), 0.0)
        previous_milepost = float(
            train.milepost
            if train.milepost is not None
            else self.minimum_milepost
        )
        direction = (train.direction or "Eastbound").strip().lower()

        stopped_for_constraint = status in {
            "Stopped at Signal",
            "Stopped at Unsafe Switch",
        }
        if stopped_for_constraint:
            train.current_signal = observed_aspect

            if observed_aspect != "Clear" or (
                unsafe_switch and observed_target is unsafe_switch
            ):
                train.speed = 0
                train.last_updated = datetime.now(timezone.utc)
                self._record_history(train, db)
                return

            train.status = "Moving"
            status = train.status
            record_event(
                db,
                event_type="train_resumed",
                title=f"{train.symbol} resumed",
                message=(
                    f"{train.symbol} resumed after signal "
                    f"{observed_target.name if observed_target else 'cleared'}."
                ),
                train_id=train.id,
                track_block_id=self._target_track_block_id(observed_target),
                metadata={
                    "milepost": previous_milepost,
                    "observed_aspect": observed_aspect,
                },
            )

        if status not in self.ACTIVE_TRAIN_STATUSES:
            self._record_history(train, db)
            return

        train.current_signal = observed_aspect
        ptc_restricted = self._ptc_communications_restricted(train, db)

        target_speed = float(
            observed_block.speed_limit
            if observed_block and observed_block.speed_limit
            else self.NORMAL_SPEED_MPH
        )
        for restriction in restrictions:
            if restriction.restriction_type != "SPEED_RESTRICTION":
                continue
            try:
                import json
                restricted_speed = int(
                    json.loads(restriction.metadata_json or "{}").get(
                        "speed_mph", self.RESTRICTED_SPEED_MPH
                    )
                )
                target_speed = min(target_speed, restricted_speed)
                train.status = "Restricted"
            except (TypeError, ValueError, json.JSONDecodeError):
                target_speed = min(target_speed, self.RESTRICTED_SPEED_MPH)

        if observed_aspect == "Stop" and observed_target:
            distance_to_stop = self._distance_to_stop_point(
                previous_milepost, direction, observed_target
            )
            target_speed = min(
                target_speed,
                self._safe_speed_for_distance(distance_to_stop),
            )
            train.status = "Braking for Signal"
            if previous_status not in {"Braking for Signal", "Stopped at Signal"}:
                record_event(
                    db,
                    event_type="train_began_braking",
                    title=f"{train.symbol} braking for signal",
                    message=(
                        f"{train.symbol} began braking for Stop "
                        f"at {observed_target.name}."
                    ),
                    train_id=train.id,
                    track_block_id=self._target_track_block_id(observed_target),
                    metadata={
                        "milepost": previous_milepost,
                        "speed_mph": previous_speed,
                    },
                )
        elif observed_aspect == "Approach":
            target_speed = min(target_speed, self.APPROACH_SPEED_MPH)
            train.status = "Restricted"
        elif ptc_restricted:
            target_speed = min(target_speed, self.RESTRICTED_SPEED_MPH)
            train.status = "Restricted - PTC Communications"
        else:
            train.status = "Moving"

        new_speed = self._move_speed_toward(previous_speed, target_speed)
        average_speed = (previous_speed + new_speed) / 2.0
        milepost_change = self._calculate_milepost_change(average_speed)
        next_milepost = (
            previous_milepost - milepost_change
            if direction == "westbound"
            else previous_milepost + milepost_change
        )

        if observed_aspect == "Stop" and observed_target:
            stop_position = self._stop_position(
                previous_milepost, direction, observed_target
            )
            would_cross = (
                next_milepost <= stop_position
                if direction == "westbound"
                else next_milepost >= stop_position
            )
            at_stop = self._distance_to_stop_point(
                previous_milepost, direction, observed_target
            ) <= 0.0005
            if would_cross or at_stop:
                train.milepost = stop_position
                train.speed = 0
                train.status = (
                    "Stopped at Unsafe Switch"
                    if isinstance(observed_target, TrackSwitch)
                    else "Stopped at Signal"
                )
                train.current_signal = "Stop"
                train.last_updated = datetime.now(timezone.utc)
                if previous_status != "Stopped at Signal":
                    record_event(
                        db,
                        event_type="train_stopped_signal",
                        title=f"{train.symbol} stopped at signal",
                        message=(
                            f"{train.symbol} stopped before "
                            f"{observed_target.name}."
                        ),
                        train_id=train.id,
                        track_block_id=self._target_track_block_id(observed_target),
                        metadata={
                            "milepost": train.milepost,
                            "signal_aspect": "Stop",
                        },
                    )
                self._record_history(train, db)
                return

        train.speed = round(new_speed, 1)

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

        train.last_updated = datetime.now(timezone.utc)

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

    def _get_route_blocks(self, train: Train, db) -> List[TrackBlock]:
        query = db.query(TrackBlock)
        subdivision = (train.subdivision or "").strip()
        track = (train.track or "").strip()
        if subdivision:
            query = query.filter(TrackBlock.subdivision == subdivision)
        if track:
            query = query.filter(TrackBlock.track == track)
        blocks = query.order_by(TrackBlock.start_milepost).all()
        if blocks:
            return blocks

        # Compatibility for databases seeded before trains carried the
        # configured territory subdivision.
        fallback = db.query(TrackBlock)
        if track:
            fallback = fallback.filter(TrackBlock.track == track)
        return fallback.order_by(TrackBlock.start_milepost).all()

    def _get_observed_block(self, train: Train, db):
        blocks = self._get_route_blocks(train, db)
        milepost = float(
            train.milepost
            if train.milepost is not None
            else self.minimum_milepost
        )
        direction = (train.direction or "Eastbound").strip().lower()

        if direction == "westbound":
            candidates = [
                block
                for block in blocks
                if float(block.end_milepost) <= milepost
            ]
            return candidates[-1] if candidates else None

        return next(
            (
                block
                for block in blocks
                if float(block.start_milepost) > milepost
            ),
            None,
        )

    def _get_unsafe_switch_ahead(self, train: Train, db):
        milepost = float(train.milepost or self.minimum_milepost)
        direction = (train.direction or "Eastbound").strip().lower()
        query = db.query(TrackSwitch).filter(
            TrackSwitch.subdivision == train.subdivision,
            TrackSwitch.track == (train.track or "Main"),
        )
        switches = [
            track_switch
            for track_switch in query.all()
            if (
                track_switch.locked
                or track_switch.position != track_switch.commanded_position
                or (track_switch.security_status or "").lower()
                == "compromised"
            )
        ]
        if direction == "westbound":
            candidates = [
                track_switch
                for track_switch in switches
                if float(track_switch.milepost) < milepost
            ]
            return max(candidates, key=lambda item: item.milepost, default=None)
        candidates = [
            track_switch
            for track_switch in switches
            if float(track_switch.milepost) > milepost
        ]
        return min(candidates, key=lambda item: item.milepost, default=None)

    @staticmethod
    def _target_track_block_id(target):
        if isinstance(target, TrackSwitch):
            return target.track_block_id
        return target.id if target else None

    def _distance_to_target(self, train, target):
        direction = (train.direction or "Eastbound").strip().lower()
        milepost = float(train.milepost or self.minimum_milepost)
        return self._distance_to_stop_point(milepost, direction, target)

    @staticmethod
    def _target_boundary(direction, target):
        if isinstance(target, TrackSwitch):
            return float(target.milepost)
        if direction == "westbound":
            return float(target.end_milepost)
        return float(target.start_milepost)

    def _stop_position(self, previous_milepost, direction, target):
        target_boundary = self._target_boundary(direction, target)
        if direction == "westbound":
            boundary = (
                target_boundary + self.SIGNAL_STOP_MARGIN_MILES
            )
            return round(min(previous_milepost, boundary), 3)

        boundary = (
            target_boundary - self.SIGNAL_STOP_MARGIN_MILES
        )
        return round(max(previous_milepost, boundary), 3)

    def _distance_to_stop_point(self, milepost, direction, target) -> float:
        stop_position = self._stop_position(milepost, direction, target)
        return max(
            milepost - stop_position
            if direction == "westbound"
            else stop_position - milepost,
            0.0,
        )

    def _safe_speed_for_distance(self, distance_miles: float) -> float:
        if distance_miles <= 0:
            return 0.0
        deceleration_mph_per_hour = (
            self.SERVICE_BRAKING_MPH_PER_SECOND * 3600.0
        )
        return sqrt(2.0 * deceleration_mph_per_hour * distance_miles)

    @staticmethod
    def _ptc_communications_restricted(train, db):
        if not train.ptc_enabled:
            return False
        gateway = db.query(OTDevice).filter(
            OTDevice.device_type == "PTC Communications Gateway"
        ).first()
        return bool(
            gateway
            and (gateway.status or "").strip().lower()
            in {"degraded", "offline", "compromised", "severe"}
        )

    def _move_speed_toward(
        self, current_speed: float, target_speed: float
    ) -> float:
        if target_speed < current_speed:
            change = self.SERVICE_BRAKING_MPH_PER_SECOND * self.interval_seconds
            return max(target_speed, current_speed - change)
        change = self.NORMAL_ACCELERATION_MPH_PER_SECOND * self.interval_seconds
        return min(target_speed, current_speed + change)

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

        now = datetime.now(timezone.utc)

        for block in blocks:
            block.occupied = False
            block.occupied_train_id = None
            block.last_updated = now

        for train in trains:
            if train.milepost is None:
                continue

            milepost = float(train.milepost)
            route_blocks = self._get_route_blocks(train, db)

            for index, block in enumerate(route_blocks):
                start_milepost = float(
                    block.start_milepost
                )
                end_milepost = float(
                    block.end_milepost
                )

                is_last_block = (
                    index == len(route_blocks) - 1
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
                    if not block.occupied:
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

        now = datetime.now(timezone.utc)

        for index, block in enumerate(blocks):
            next_block = (
                blocks[index + 1]
                if index + 1 < len(blocks)
                else None
            )

            communications_status = (
                block.communications_status or "Online"
            ).strip().lower()
            security_status = (
                block.security_status or "Healthy"
            ).strip().lower()

            if security_status == "compromised":
                indication = "Stop"
            elif communications_status != "online":
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

        block_compromised = (
            (block.security_status or "").strip().lower()
            == "compromised"
        )
        communications_degraded = (
            (block.communications_status or "").strip().lower()
            != "online"
        )

        if block_compromised or communications_degraded:
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
            timestamp=datetime.now(timezone.utc),
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
                train.last_updated = datetime.now(timezone.utc)

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
