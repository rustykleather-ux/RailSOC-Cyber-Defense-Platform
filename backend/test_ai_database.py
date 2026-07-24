from pprint import pprint

from database import SessionLocal
from models import Incident
from ai_assistant import analyze_single_incident


def main():
    db = SessionLocal()

    try:
        incident = (
            db.query(Incident)
            .order_by(Incident.id.desc())
            .first()
        )

        if incident is None:
            print("No incidents were found in ot_platform.db.")
            return

        print(f"Testing incident ID: {incident.id}")

        result = analyze_single_incident(incident)

        pprint(result)

    finally:
        db.close()


if __name__ == "__main__":
    main()