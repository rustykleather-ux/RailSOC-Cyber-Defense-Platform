from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

alerts = [
    {
        "id": 1,
        "severity": "Critical",
        "device": "PLC-2",
        "message": "Firmware is outdated",
        "time": datetime.now().isoformat()
    },
    {
        "id": 2,
        "severity": "High",
        "device": "PTC Radio Gateway",
        "message": "Communication Lost",
        "time": datetime.now().isoformat()
    },
    {
        "id": 3,
        "severity": "Medium",
        "device": "Engineering Workstation",
        "message": "Multiple Failed Logins",
        "time": datetime.now().isoformat()
    }
]

@router.get("/alerts")
def get_alerts():
    return alerts