import { useEffect, useState } from "react";
import axios from "axios";
import "./App.css";
import Header from "./components/Header";
import DashboardCards from "./components/DashboardCards";
import DemoControls from "./components/DemoControls";
import NetworkTopology from "./components/NetworkTopology";
import LivePlantStatus from "./components/LivePlantStatus";
import DeviceInventory from "./components/DeviceInventory";
import VulenrabilityTable from "./components/VulnerabilityTable";
import AlertsPanel from "./components/AlertsPanel";

function App() {
  const [devices, setDevices] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [vulnerabilities, setVulnerabilities] = useState([]);
  const [plantStatus, setPlantStatus] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      loadPlantStatus();
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const loadPlantStatus = () => {
    axios
      .get("http://127.0.0.1:8000/plant-status")
      .then((res) => setPlantStatus(Array.isArray(res.data) ? res.data : []))
      .catch((err) => console.error("Plant Status Error:", err));
  };

  const loadData = () => {
    loadPlantStatus();

    axios
      .get("http://127.0.0.1:8000/devices")
      .then((res) => setDevices(Array.isArray(res.data) ? res.data : []))
      .catch((err) => console.error("Devices Error:", err));

    axios
      .get("http://127.0.0.1:8000/vulnerabilities")
      .then((res) =>
        setVulnerabilities(Array.isArray(res.data) ? res.data : [])
      )
      .catch((err) => console.error("Vulnerabilities Error:", err));

    axios
      .get("http://127.0.0.1:8000/dashboard")
      .then((res) => setDashboard(res.data || null))
      .catch((err) => console.error("Dashboard Error:", err));

    axios
      .get("http://127.0.0.1:8000/alerts")
      .then((res) => setAlerts(Array.isArray(res.data) ? res.data : []))
      .catch((err) => console.error("Alerts Error:", err));
  };

  const simulateAttack = (attackType) => {
    axios
      .post(`http://127.0.0.1:8000/simulate-attack/${attackType}`)
      .then(() => loadData())
      .catch((err) => console.error("Simulation Error:", err));
  };

  const resetDemo = () => {
    axios
      .post("http://127.0.0.1:8000/reset-demo")
      .then(() => loadData())
      .catch((err) => console.error("Reset Error:", err));
    
    const risk = device.calculated_risk || device.risk_level;

    if (risk === "Critical") return "critical";
    if (risk === "High") return "warning";
    if (risk === "Medium") return "medium";

    return "healthy";
  };

  return (
    <div className="app">
      <Header />

      <DashboardCards dashboard={dashboard} />

      <DemoControls simulateAttack={simulateAttack} resetDemo={resetDemo} />

      <NetworkTopology devices={devices} />

      <LivePlantStatus plantStatus={plantStatus} />

      <DeviceInventory devices={devices} />

      <VulenrabilityTable vulnerabilities={vulnerabilities} />

      <AlertsPanel alerts={alerts} />
      
    </div>
  );
}

export default App;