import threading
import time
from datetime import datetime

from database import SessionLocal
from models import Train, TrainHistory


class TrainSimulationEngine:
    def __init__(
        self,
        interval_seconds: int = 3,
        minimum_milepost: float = 78.45,
        maximum_milepost: float = 95.2,
    ):
        self.interval_seconds = interval_seconds
        self.minimum_milepost = minimum_milepost
        self.maximum_milepost = maximum_milepost

        self._running = False
        self._thread = None
        self._lock = threading.Lock()

        # Ordered railroad infrastructure.
        self.track_events = [
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

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> bool:
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

            return True

    def stop(self) -> bool:
        with self._lock:
            if not self._running:
                return False

            self._running = False

            return True

    def _run_loop(self):
        while self._running:
            try:
                self.tick()
            except Exception as exc:
                print(f"[TRAIN SIMULATION ERROR] {exc}")

            time.sleep(self.interval_seconds)

    def tick(self):
        db = SessionLocal()

        try:
            trains = db.query(Train).all()

            for train in trains:
                self._update_train(train, db)

            db.commit()

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

    def _update_train(self, train: Train, db):
        if train.status not in ["Moving", "Restricted"]:
            self._record_history(train, db)
            return

        if train.speed is None or train.speed <= 0:
            train.speed = 0
            train.status = "Stopped"
            train.current_signal = "Stop"
            train.last_updated = datetime.utcnow()

            self._record_history(train, db)
            return

        previous_milepost = float(train.milepost or self.minimum_milepost)

        milepost_change = self._calculate_milepost_change(train.speed)

        direction = (train.direction or "Eastbound").strip().lower()

        if direction == "westbound":
            next_milepost = previous_milepost - milepost_change
        else:
            next_milepost = previous_milepost + milepost_change

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
            train.current_signal = self._calculate_signal_state(train)

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
                db=db,
            )

        self._record_history(train, db)

    def _calculate_milepost_change(self, speed_mph: int) -> float:
        """
        Convert train speed into distance traveled during one simulation tick.
        """

        hours_per_tick = self.interval_seconds / 3600.0

        return float(speed_mph) * hours_per_tick

    def _calculate_signal_state(self, train: Train) -> str:
        if train.status == "Restricted":
            return "Approach"

        if not train.ptc_enabled:
            return "Restricted"

        if train.speed is None or train.speed <= 0:
            return "Stop"

        if train.speed <= 25:
            return "Approach"

        return "Clear"

    def _get_crossed_track_events(
        self,
        previous_milepost: float,
        current_milepost: float,
        direction: str,
    ):
        """
        Return every track event crossed during one simulation tick.

        Eastbound:
            lowest milepost to highest milepost

        Westbound:
            highest milepost to lowest milepost
        """

        normalized_direction = (direction or "eastbound").strip().lower()

        if normalized_direction == "westbound":
            crossed_events = [
                event
                for event in self.track_events
                if current_milepost <= event["milepost"] < previous_milepost
            ]

            return sorted(
                crossed_events,
                key=lambda event: event["milepost"],
                reverse=True,
            )

        crossed_events = [
            event
            for event in self.track_events
            if previous_milepost < event["milepost"] <= current_milepost
        ]

        return sorted(
            crossed_events,
            key=lambda event: event["milepost"],
        )

    def _process_track_event(
        self,
        train: Train,
        event: dict,
        db,
    ):
        event_type = event["type"]
        event_name = event["name"]
        event_milepost = event["milepost"]

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
    ):
        train.current_signal = self._calculate_signal_state(train)

        print(
            f"[SIGNAL] {train.symbol} passed {event_name} "
            f"at MP {event_milepost}. "
            f"Signal indication: {train.current_signal}"
        )

    def _process_crossing_event(
        self,
        train: Train,
        event_name: str,
        event_milepost: float,
    ):
        print(
            f"[CROSSING] {train.symbol} entered {event_name} "
            f"at MP {event_milepost}. "
            "Crossing activation sequence triggered."
        )

    def _process_detector_event(
        self,
        train: Train,
        event_name: str,
        event_milepost: float,
    ):
        print(
            f"[DETECTOR] {train.symbol} passed {event_name} "
            f"at MP {event_milepost}. "
            "Detector inspection completed."
        )

    def _record_history(self, train: Train, db):
        history = TrainHistory(
            train_id=train.id,
            milepost=float(train.milepost),
            speed=int(train.speed or 0),
            status=train.status,
            current_signal=train.current_signal,
            authority=train.authority,
            ptc_enabled=train.ptc_enabled,
            timestamp=datetime.utcnow(),
        )

        db.add(history)

    def reset_trains(self):
        db = SessionLocal()

        try:
            trains = db.query(Train).order_by(Train.id).all()

            for index, train in enumerate(trains):
                direction = (
                    train.direction or "Eastbound"
                ).strip().lower()

                if direction == "westbound":
                    train.milepost = round(
                        self.maximum_milepost - (index * 0.5),
                        3,
                    )
                else:
                    train.milepost = round(
                        self.minimum_milepost + (index * 0.5),
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

            db.commit()

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()


train_simulation = TrainSimulationEngine(
    interval_seconds=3,
    minimum_milepost=78.45,
    maximum_milepost=95.2,
)