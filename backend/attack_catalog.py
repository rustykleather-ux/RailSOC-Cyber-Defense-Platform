attack_catalog = {
    "logic_modification": {
        "attack_id": "logic_modification",
        "name": "Unauthorized Logic Modification",
        "description": "Simulating unauthorized modification of controller logic.",
        "severity": "Critical",
        "mitre_id": "T0859",
        "mitre_name": "Modify Controller Tasking",
        "compatible_types": ["Signal Contoller", 
                             "PLC", 
                             "Switch Controller"],
        "condition": "Configuration Drift",
    },
    "credential_abuse": {
        "attack_id": "credential_abuse",
        "name": "Credential Abuse",
        "description": "Simulating unauthorized use of valid credentials.",
        "severity": "High",
        "mitre_id": "T1078",
        "mitre_name": "Valid Accounts",
        "compatible_types": ["Workstation", "Server", "Network Device"],
        "condition": "Unusual Login Activity"
    },
    "network_recon": {
        "attack_id": "network_recon",
        "name": "Network Reconnaissance",
        "description": "Simulating network reconnaissance activities.",
        "severity": "Medium",
        "mitre_id": "T1046",
        "mitre_name": "Network Service Scanning",
        "compatible_types": ["Workstation", "Server", "Network Device"],
        "condition": "Unusual Network Traffic"
    },

    "firmware_tampering": {
        "attack_id": "firmware_tampering",
        "name": "Firmware Tampering",
        "description": "Simulating unauthorized tampering with device firmware.",
        "severity": "Critical",
        "mitre_id": "T1609",
        "mitre_name": "Firmware Modification",
        "compatible_types": ["PLC", "Switch Controller", "IoT Device"],
        "condition": "Unexpected Firmware Changes"
    },
    
    "Denial_of_Service": {
        "attack_id": "Denial_of_Service",
        "name": "Denial of Service",
        "description": "Simulating a denial of service attack.",
        "severity": "High",
        "mitre_id": "T1499",
        "mitre_name": "Endpoint Denial of Service",
        "compatible_types": ["Server", "Network Device"],
        "condition": "Service Unavailability"
    },

    "communication_failure": {
        "attack_id": "communication_failure",
        "name": "Communication Failure",
        "description": "Simulating a communication failure between devices.",
        "severity": "Medium",
        "mitre_id": "T1601",
        "mitre_name": "Communication Disruption",
        "compatible_types": ["PLC", "Switch Controller", "IoT Device"],
        "condition": "Unexpected Communication Loss"
    },

    "malware_injection": {
        "attack_id": "malware_injection",
        "name": "Malware Injection",
        "description": "Simulating the injection of malware into a system.",
        "severity": "Critical",
        "mitre_id": "T1059",
        "mitre_name": "Command and Scripting Interpreter",
        "compatible_types": ["Workstation", "Server"],
        "condition": "Unexpected Process Execution"
    },

    "ransomware_attack": {
        "attack_id": "ransomware_attack",
        "name": "Ransomware Attack",
        "description": "Simulating a ransomware attack on a system.",
        "severity": "Critical",
        "mitre_id": "T1486",
        "mitre_name": "Data Encrypted for Impact",
        "compatible_types": ["Workstation", "Server"],
        "condition": "Unexpected File Encryption"
    },

    "sensor_tampering": {
        "attack_id": "sensor_tampering",
        "name": "Sensor Tampering",
        "description": "Simulating tampering with sensor data.",
        "severity": "High",
        "mitre_id": "T1602",
        "mitre_name": "Sensor Manipulation",
        "compatible_types": ["IoT Device", "PLC"],
        "condition": "Unexpected Sensor Readings"
    },

    "power_fluctuation": {
        "attack_id": "power_fluctuation",
        "name": "Power Fluctuation",
        "description": "Simulating power fluctuations affecting device operation.",
        "severity": "Medium",
        "mitre_id": "T1603",
        "mitre_name": "Power Disruption",
        "compatible_types": ["PLC", "Switch Controller", "IoT Device"],
        "condition": "Unexpected Power Variations"
    },

    "braute_force_attack": {
        "attack_id": "brute_force_attack",
        "name": "Brute Force Attack",
        "description": "Simulating a brute force attack on authentication mechanisms.",
        "severity": "High",
        "mitre_id": "T1110",
        "mitre_name": "Brute Force",
        "compatible_types": ["Workstation", "Server", "Network Device"],
        "condition": "Multiple Failed Login Attempts"
    },

    "data_Exfiltration": {
        "attack_id": "Data_Exfiltration",
        "name": "Data Exfiltration",
        "description": "Simulating unauthorized data exfiltration from a system.",
        "severity": "Critical",
        "mitre_id": "T1041",
        "mitre_name": "Exfiltration Over C2 Channel",
        "compatible_types": ["Workstation", "Server"],
        "condition": "Unexpected Data Transfer"
    },

    "door_access": {
        "attack_id": "door_access",
        "name": "Unauthorized Door Access",
        "description": "Simulating unauthorized access to restricted door areas.",
        "severity": "High",
        "mitre_id": "T1078",
        "mitre_name": "Valid Accounts",
        "compatible_types": ["Access Control Device"],
        "condition": "Unexpected Door Access"
    }


}