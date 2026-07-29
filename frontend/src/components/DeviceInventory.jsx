function DeviceInventory({ devices }) {
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
            <th>Capabilities</th>
            <th>Relationships</th>
            <th>Last Communication</th>
          </tr>
        </thead>

        <tbody>
          {(
  Array.isArray(devices)
    ? devices
    : Array.isArray(devices?.devices)
    ? devices.devices
    : []
).map((device) => (
            <tr key={device.id}>
              <td>{device.name}</td>

              <td>{device.ip_address}</td>

              <td>{device.device_type}</td>

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

              <td>{device.location}</td>

              <td>
                <div className="asset-chip-list">
                  {(device.capabilities ?? []).slice(0, 3).map((capability) => (
                    <span key={capability}>{capability.replaceAll("_", " ")}</span>
                  ))}
                </div>
              </td>

              <td>{device.relationships?.length ?? 0}</td>

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
