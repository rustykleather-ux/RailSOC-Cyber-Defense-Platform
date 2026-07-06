function DeviceInventory({ devices }) {
  const displayName = (name) => {
    switch (name) {
      case "SCADA Server":
        return "Dispatch SCADA Server";

      case "PLC-1":
        return "Signal Controller 14A";

      case "PLC-2":
        return "Grade Crossing Controller MP 82.4";

      case "Solar Inverter":
        return "PTC Radio Gateway";

      case "Engineering Workstation":
        return "Rail Engineering Workstation";

      default:
        return name || "Unknown Asset";
    }
  };

  const displayType = (type) => {
    switch (type) {
      case "SCADA":
        return "Dispatch System";

      case "PLC":
        return "Signal Controller";

      case "Inverter":
        return "Communications Gateway";

      case "Workstation":
        return "Engineering Station";

      default:
        return type || "Rail Asset";
    }
  };

  const displayLocation = (name, location) => {
  switch (name) {
    case "SCADA Server":
      return "West Dispatch Center";

    case "PLC-1":
      return "East Signal District";

    case "PLC-2":
      return "Prairie Subdivision - MP 82.4";

    case "Solar Inverter":
      return "Wayside Communications Hut";

    case "Engineering Workstation":
      return "Maintenance Facility Alpha";

    default:
      return location || "Unknown Rail Location";
  }
};
  
  return (
    <>
      <h2>Railroad OT Asset Inventory</h2>

      <table>
        <thead>
          <tr>
            <th>Asset</th>
            <th>IP Address</th>
            <th>Asset Type</th>
            <th>Vendor</th>
            <th>Status</th>
            <th>Risk</th>
            <th>Risk Score</th>
            <th>Calculated Risk</th>
            <th>Firmware</th>
            <th>Location</th>
            <th>Last Communication</th>
          </tr>
        </thead>

        <tbody>
          {(devices || []).map((device) => (
            <tr key={device.id}>
              <td>{displayName(device.name)}</td>

              <td>{device.ip_address}</td>

              <td>{displayType(device.device_type)}</td>

              <td>{device.vendor}</td>

              <td>{device.status}</td>

              <td>
                <span
                  className={`badge ${(device.risk_level || "low").toLowerCase()}`}
                >
                  {device.risk_level || "Unknown"}
                </span>
              </td>

              <td>{device.risk_score}</td>

              <td>
                <span
                  className={`badge ${(device.calculated_risk || "low").toLowerCase()}`}
                >
                  {device.calculated_risk || "Unknown"}
                </span>
              </td>

              <td>{device.firmware_version}</td>

              <td>{displayLocation(device.name, device.location)}</td>

              <td>
                {device.last_seen
                  ? new Date(device.last_seen).toLocaleString()
                  : "Unknown"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

export default DeviceInventory;