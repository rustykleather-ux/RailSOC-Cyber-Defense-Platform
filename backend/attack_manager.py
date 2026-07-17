from datetime import datetime
from typing import Optional


active_attacks = []


def launch_attack(
    attack: dict,
    targets: list,
    notes: Optional[str] = None,
):
    attack_id = len(active_attacks) + 1

    attack_instance = {
        "id": attack_id,
        "attack_id": attack["attack_id"],
        "attack_name": attack["name"],
        "severity": attack["severity"],
        "mitre_id": attack["mitre_id"],
        "mitre_name": attack["mitre_name"],
        "target_ids": [
            target.id
            for target in targets
        ],
        "target_names": [
            target.name
            for target in targets
        ],
        "notes": notes,
        "status": "Running",
        "started_at": datetime.utcnow().isoformat(),
    }

    active_attacks.append(attack_instance)

    return attack_instance

def get_active_attacks():
        return active_attacks