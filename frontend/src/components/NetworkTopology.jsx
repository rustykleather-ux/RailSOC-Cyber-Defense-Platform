function NetworkTopology({ devices }) {
  const getDevice = (name) => {
    return (devices || []).find((device) => device.name === name);
  };

  const getNodeClass = (device) => {
    if (!device) return "unknown";
    if (device.status === "Offline") return "critical";

    const risk = device.calculated_risk || device.risk_level;

    if (risk === "Critical") return "critical";
    if (risk === "High") return "warning";
    if (risk === "Medium") return "medium";

    return "healthy";
  };

  return (
    <>
      <h2>OT Network Topology</h2>

      <div className="topology">
        <div className="topology-node firewall">Firewall</div>

        <div className="topology-line"></div>

        <div className={`topology-node ${getNodeClass(getDevice("SCADA Server"))}`}>
          SCADA Server
          <span>{getDevice("SCADA Server")?.ip_address || "Unknown IP"}</span>
        </div>

        <div className="topology-branches">
          {["PLC-1", "PLC-2", "Solar Inverter"].map((name) => (
            <div className="branch" key={name}>
              <div className="topology-line"></div>
              <div className={`topology-node ${getNodeClass(getDevice(name))}`}>
                {name}
                <span>{getDevice(name)?.ip_address || "Unknown IP"}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="topology-branches">
          <div className="branch">
            <div className="topology-line"></div>
            <div
              className={`topology-node ${getNodeClass(
                getDevice("Engineering Workstation")
              )}`}
            >
              Engineering Workstation
              <span>
                {getDevice("Engineering Workstation")?.ip_address ||
                  "Unknown IP"}
              </span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default NetworkTopology;