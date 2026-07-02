function DeviceInventory({ devices }) {
  return (
    <>
      <h2>OT Asset Inventory</h2>

      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>IP Address</th>
            <th>Type</th>
            <th>Vendor</th>
            <th>Status</th>
            <th>Risk</th>
            <th>Risk Score</th>
            <th>Calculated Risk</th>
            <th>Firmware</th>
            <th>Location</th>
            <th>Last Seen</th>
          </tr>
        </thead>

        <tbody>
          {(devices || []).map((device) => (
            <tr key={device.id}>
              <td>{device.name}</td>
              <td>{device.ip_address}</td>
              <td>{device.device_type}</td>
              <td>{device.vendor}</td>
              <td>{device.status}</td>
              <td>
                <span className={`badge ${(device.risk_level || "low").toLowerCase()}`}>
                  {device.risk_level || "Unknown"}
                </span>
              </td>
              <td>{device.risk_score}</td>
              <td>
                <span className={`badge ${(device.calculated_risk || "low").toLowerCase()}`}>
                  {device.calculated_risk || "Unknown"}
                </span>
              </td>
              <td>{device.firmware_version}</td>
              <td>{device.location}</td>
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