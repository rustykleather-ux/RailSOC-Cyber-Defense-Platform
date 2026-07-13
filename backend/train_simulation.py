import threading
import time
from datetime import datetime

from database import SessionLocal
from models import Train, TrainHistory


class TrainSimulationEngine:
    def __init__(
        self,
        interval_seconds: int = 3,
        minimum_milepost: float = 80.0,
        maximum_milepost: float = 95.2,
    ):
        self.interval_seconds = interval_seconds
        self.minimum_milepost = minimum_milepost
        self.maximum_milepost = maximum_milepost

        self._running = False
        self._thread = None
        self._lock = threading.Lock()

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
                print(f"Train simulation error: {exc}")

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
            train.status = "Stopped"
            train.speed = 0
            train.last_updated = datetime.utcnow()

            self._record_history(train, db)
            return

        milepost_change = self._calculate_milepost_change(train.speed)

        if train.direction == "Westbound":
            next_milepost = train.milepost - milepost_change
        else:
            next_milepost = train.milepost + milepost_change

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
            train.milepost = round(next_milepost, 2)
            train.current_signal = self._calculate_signal_state(train)

        train.last_updated = datetime.utcnow()

        self._record_history(train, db)

    def _calculate_milepost_change(self, speed_mph: int) -> float:
        hours_per_tick = self.interval_seconds / 3600
        return speed_mph * hours_per_tick

    def _calculate_signal_state(self, train: Train) -> str:
        if train.status == "Restricted":
            return "Approach"

        if not train.ptc_enabled:
            return "Restricted"

        if train.speed <= 0:
            return "Stop"

        if train.speed <= 25:
            return "Approach"

        return "Clear"

    def _record_history(self, train: Train, db):
        history = TrainHistory(
            train_id=train.id,
            milepost=train.milepost,
            speed=train.speed,
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
            trains = db.query(Train).all()

            for index, train in enumerate(trains):
                if train.direction == "Westbound":
                    train.milepost = self.maximum_milepost - (index * 0.5)
                else:
                    train.milepost = self.minimum_milepost + (index * 0.5)

                train.speed = 40
                train.status = "Moving"
                train.ptc_enabled = True
                train.authority = "Main Track"
                train.current_signal = "Clear"
                train.last_updated = datetime.utcnow()

            db.query(TrainHistory).delete()
            db.commit()

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()


train_simulation = TrainSimulationEngine(
    interval_seconds=3,
    minimum_milepost=80.0,
    maximum_milepost=95.2,
)