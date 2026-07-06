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

  const railNodes = [
    {
      name: "Signal Controller 14A",
      detail: "East Signal District",
    },
    {
      name: "Grade Crossing Controller MP 82.4",
      detail: "Prairie Subdivision",
    },
    {
      name: "PTC Radio Gateway",
      detail: "Wayside Communications Hut",
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

        <div
          className={`topology-node ${getNodeClass(
            getDevice("Dispatch SCADA Server")
          )}`}
        >
          Dispatch SCADA Server
          <span>
            {getDevice("Dispatch SCADA Server")?.ip_address || "Unknown IP"}
          </span>
        </div>

        <div className="topology-branches">
          {railNodes.map((node) => {
            const device = getDevice(node.name);

            return (
              <div className="branch" key={node.name}>
                <div className="topology-line"></div>

                <div className={`topology-node ${getNodeClass(device)}`}>
                  {node.name}
                  <span>{node.detail}</span>
                  <span>{device?.ip_address || "Unknown IP"}</span>
                </div>
              </div>
            );
          })}
        </div>

        <div className="topology-branches">
          <div className="branch">
            <div className="topology-line"></div>

            <div
              className={`topology-node ${getNodeClass(
                getDevice("Rail Engineering Workstation")
              )}`}
            >
              Rail Engineering Workstation
              <span>Remote Maintenance Access</span>
              <span>
                {getDevice("Rail Engineering Workstation")?.ip_address ||
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