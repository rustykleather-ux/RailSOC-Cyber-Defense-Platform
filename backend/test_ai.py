from ai_assistant import analyze_single_incident

test_incident = {
    "id": 1,
    "severity": "High",
    "status": "Open",
    "device": "Signal Controller 14A",
    "alert_type": "Communication Loss",
    "message": "Controller communication was lost.",
    "acknowledged": False,
    "assigned_to": "Unassigned",
    "investigation_notes": "",
    "mitre_technique": "T0881 - Service Stop",
}

result = analyze_single_incident(test_incident)

from pprint import pprint
pprint(result)