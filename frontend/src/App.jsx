import { useEffect, useState } from "react";
import "./App.css";

import Header from "./components/Header";
import EnvironmentOverview from "./components/EnviromentOverview";
import DashboardCards from "./components/DashboardCards";
import DemoControls from "./components/DemoControls";
import NetworkTopology from "./components/NetworkTopology";
import LivePlantStatus from "./components/LivePlantStatus";
import DeviceInventory from "./components/DeviceInventory";
import VulnerabilityTable from "./components/VulnerabilityTable";
import AlertsPanel from "./components/AlertsPanel";
import IncidentCenter from "./components/IncidentCenter";

import {
  getIncidents,
  acknowledgeIncidentRequest,
  assignIncidentRequest,
  updateIncidentNotesRequest,
  closeIncidentRequest,
} from "./services/incidentService";

import { getDevices } from "./services/deviceService";
import { getDashboard } from "./services/dashboardService";
import { getAlerts } from "./services/alertService";
import { getVulnerabilities } from "./services/vulnerabilityService";
import { getPlantStatus } from "./services/telemetryService";

import {
  simulateAttackRequest,
  resetDemoRequest,
} from "./services/simulationService";

function App() {
  const [devices, setDevices] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [vulnerabilities, setVulnerabilities] = useState([]);
  const [plantStatus, setPlantStatus] = useState([]);
  const [incidents, setIncidents] = useState([]);

  const loadPlantStatus = async () => {
    try {
      const res = await getPlantStatus();
      setPlantStatus(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      console.error("TrackSentinel Telemetry Error:", err);
    }
  };

  const loadData = async () => {
    try {
      await loadPlantStatus();

      const [
        devicesRes,
        vulnerabilitiesRes,
        dashboardRes,
        alertsRes,
        incidentsRes,
      ] = await Promise.all([
        getDevices(),
        getVulnerabilities(),
        getDashboard(),
        getAlerts(),
        getIncidents(),
      ]);

      setDevices(Array.isArray(devicesRes.data) ? devicesRes.data : []);
      setVulnerabilities(
        Array.isArray(vulnerabilitiesRes.data)
          ? vulnerabilitiesRes.data
          : []
      );
      setDashboard(dashboardRes.data || null);
      setAlerts(Array.isArray(alertsRes.data) ? alertsRes.data : []);
      setIncidents(Array.isArray(incidentsRes.data) ? incidentsRes.data : []);
    } catch (err) {
      console.error("TrackSentinel Load Data Error:", err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      loadPlantStatus();
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const simulateAttack = async (attackType) => {
    try {
      await simulateAttackRequest(attackType);
      await loadData();
    } catch (err) {
      console.error("TrackSentinel Simulation Error:", err);
    }
  };

  const resetDemo = async () => {
    try {
      await resetDemoRequest();
      await loadData();
    } catch (err) {
      console.error("TrackSentinel Reset Error:", err);
    }
  };

  const acknowledgeIncident = async (incidentId) => {
    try {
      await acknowledgeIncidentRequest(incidentId);
      await loadData();
    } catch (err) {
      console.error("TrackSentinel Acknowledge Error:", err);
    }
  };

  const assignIncident = async (incidentId, assignedTo) => {
    try {
      await assignIncidentRequest(incidentId, assignedTo);
      await loadData();
    } catch (err) {
      console.error("TrackSentinel Assign Incident Error:", err);
    }
  };

  const updateIncidentNotes = async (incidentId, notes) => {
    try {
      await updateIncidentNotesRequest(incidentId, notes);
      await loadData();
    } catch (err) {
      console.error("TrackSentinel Update Notes Error:", err);
    }
  };

  const closeIncident = async (incidentId, closedBy) => {
    try {
      await closeIncidentRequest(incidentId, closedBy);
      await loadData();
    } catch (err) {
      console.error("TrackSentinel Close Incident Error:", err);
    }
  };

  return (
  <div className="app-shell">
    <aside className="sidebar">
      <div className="sidebar-brand">
        <img src="/logo.png" alt="TrackSentinel" />
        <div>
          <strong>TrackSentinel</strong>
          <span>RailSOC Platform</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <a className="active" href="#overview">Dashboard</a>
        <a href="#topology">Railroad Topology</a>
        <a href="#telemetry">Live Telemetry</a>
        <a href="#alerts">Security Alerts</a>
        <a href="#incidents">Incident Center</a>
        <a href="#assets">OT Assets</a>
        <a href="#vulnerabilities">Vulnerabilities</a>
        <a href="#training">Training Exercises</a>
        <a href="#reports">Reports</a>
        <a href="#settings">Settings</a>
      </nav>
    </aside>

    <div className="app-content">
      <Header />

      <main className="railsoc-main">
        <div id="overview">
          <EnvironmentOverview
            dashboard={dashboard}
            alerts={alerts}
            incidents={incidents}
            vulnerabilities={vulnerabilities}
          />
        </div>

        <div id="training">
          <DemoControls
            simulateAttack={simulateAttack}
            resetDemo={resetDemo}
          />
        </div>

        <div className="dashboard-layout">
          <div className="dashboard-primary">
            <div id="topology">
              <NetworkTopology devices={devices} />
            </div>

            <div id="telemetry">
              <LivePlantStatus plantStatus={plantStatus} />
            </div>
          </div>

          <div className="dashboard-secondary">
            <div id="alerts">
              <AlertsPanel alerts={alerts} />
            </div>

            <div id="incidents">
              <IncidentCenter
                incidents={incidents}
                acknowledgeIncident={acknowledgeIncident}
                assignIncident={assignIncident}
                updateIncidentNotes={updateIncidentNotes}
                closeIncident={closeIncident}
              />
            </div>
          </div>
        </div>

        <div id="assets">
          <DeviceInventory devices={devices} />
        </div>

        <div id="vulnerabilities">
          <VulnerabilityTable vulnerabilities={vulnerabilities} />
        </div>

        <footer className="app-footer">
          TrackSentinel v1.0 · Railroad OT Cyber Defense Platform · Portfolio Demonstration
        </footer>
      </main>
    </div>
  </div>
);
}

export default App;