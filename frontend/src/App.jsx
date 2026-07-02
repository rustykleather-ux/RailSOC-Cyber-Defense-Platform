import { useEffect, useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [devices, setDevices] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [vulnerabilities, setVulnerabilities] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = () => {
    axios
      .get("http://127.0.0.1:8000/devices")
      .then((res) => setDevices(res.data))
      .catch((err) => console.error("Devices Error:", err));
    
    

    axios
      .get("http://127.0.0.1:8000/dashboard")
      .then((res) => setDashboard(res.data))
      .catch((err) => console.error("Dashboard Error:", err));

    axios
      .get("http://127.0.0.1:8000/alerts")
      .then((res) => setAlerts(res.data))
      .catch((err) => console.error("Alerts Error:", err));
  };

 
  return (
    <div className="app">
      <h1>Industrial Cyber Defense Platform</h1>
      <p className="subtitle">
        OT / IT Security Monitoring Dashboard
      </p>

      {dashboard && (
  <div className="cards">
    <div className="card">
      <span>Total Devices</span>
      <strong>{dashboard.total_devices}</strong>
    </div>

    <div className="card">
      <span>Online Devices</span>
      <strong>{dashboard.online_devices}</strong>
    </div>

    <div className="card warning">
      <span>Offline Devices</span>
      <strong>{dashboard.offline_devices}</strong>
    </div>

    <div className="card danger">
      <span>High Risk Devices</span>
      <strong>{dashboard.high_risk_devices}</strong>
    </div>

    <div className="card danger">
      <span>Open Vulnerabilities</span>
      <strong>{dashboard.open_vulnerabilities}</strong>
    </div>
  </div>

      )}

      {/* Device Inventory */}
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
            <th>Firmware</th>
            <th>Location</th>
            <th>Last Seen</th>
          </tr>
        </thead>

        <tbody>
          {devices.map((device) => (
            <tr key={device.id}>
              <td>{device.name}</td>
              <td>{device.ip_address}</td>
              <td>{device.device_type}</td>
              <td>{device.vendor}</td>
              <td>{device.status}</td>
              <td>{device.risk_level}</td>
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

      {/* Security Alerts */}
      <h2>Active Security Alerts</h2>

      <div className="alerts">
        {alerts.length === 0 ? (
          <div className="alert">
            <strong>No Active Alerts</strong>
          </div>
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              className={`alert ${(alert.severity || "low").toLowerCase()}`}
            >
              <h3>{alert.device}</h3>

              <p>
                <strong>Severity:</strong> {alert.severity}
              </p>

              <p>
                <strong>Alert:</strong> {alert.message}
              </p>

              <small>
                {alert.time
                  ? new Date(alert.time).toLocaleString()
                  : "Unknown"}
              </small>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default App;