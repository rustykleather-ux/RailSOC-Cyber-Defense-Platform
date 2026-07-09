function NetworkTopology({ devices }) {
  const getDevice = (name) => {
    return (devices || []).find((device) => device.name === name);
  };

  const getNodeClass = (device) => {
    if (!device) return "unknown";
    if (device.status === "Offline" || device.status === "Degraded")
      return "critical";

    const risk = device.calculated_risk || device.risk_level;

    if (risk === "Critical") return "critical";
    if (risk === "High") return "warning";
    if (risk === "Medium") return "medium";

    return "healthy";
  };

  const groups = [
    {
      title: "Operations Core",
      nodes: [
        "Dispatch SCADA Server",
        "Operations Historian",
        "OT Jump Server",
      ],
    },
    {
      title: "Signal & Train Control",
      nodes: [
        "Signal Controller 14A",
        "Signal Controller 14B",
        "Signal Controller 15C",
        "Grade Crossing Controller MP 82.4",
        "Grade Crossing Controller MP 87.1",
        "Switch Machine Controller",
      ],
    },
    {
      title: "Communications",
      nodes: [
        "PTC Radio Gateway",
        "Microwave Radio",
        "Fiber Distribution Switch",
      ],
    },
    {
      title: "Power, Safety & Infrastructure",
      nodes: [
        "UPS System",
        "Backup Generator PLC",
        "Fire Detection Panel",
        "Hydrogen Gas Detector",
        "Flood Detection Sensor",
        "Cabinet Intrusion Sensor",
        "Bridge Structural Monitor",
        "Hot Bearing Detector",
      ],
    },
    {
      title: "Engineering Access",
      nodes: ["Rail Engineering Workstation"],
    },
  ];

  return (
    <>
      <h2>Railroad OT Network Topology</h2>

      <div className="topology">
        <div className="topology-node firewall">
          Enterprise / OT Firewall
          <span>IT/OT Boundary</span>
        </div>

        <div className="topology-line"></div>

        <div className="topology-zone-stack">
          {groups.map((group) => (
            <section className="topology-zone" key={group.title}>
              <h3>{group.title}</h3>

              <div className="topology-zone-grid">
                {group.nodes.map((name) => {
                  const device = getDevice(name);

                  return (
                    <div
                      key={name}
                      className={`topology-node ${getNodeClass(device)}`}
                    >
                      {name}
                      <span>{device?.device_type || "Unknown Type"}</span>
                      <span>{device?.ip_address || "Unknown IP"}</span>
                    </div>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      </div>
    </>
  );
}

export default NetworkTopology;