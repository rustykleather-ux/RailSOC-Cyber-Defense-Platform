import { useEffect, useState } from "react";
import "./App.css";

import Header from "./components/Header";
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
    <div className="app">
      <Header />

      <main className="railsoc-main">
        <DashboardCards dashboard={dashboard} />

        <DemoControls simulateAttack={simulateAttack} resetDemo={resetDemo} />

        <NetworkTopology devices={devices} />

        <LivePlantStatus plantStatus={plantStatus} />

        <IncidentCenter
          incidents={incidents}
          acknowledgeIncident={acknowledgeIncident}
          assignIncident={assignIncident}
          updateIncidentNotes={updateIncidentNotes}
          closeIncident={closeIncident}
        />

        <DeviceInventory devices={devices} />

        <VulnerabilityTable vulnerabilities={vulnerabilities} />

        <AlertsPanel alerts={alerts} />
      </main>

      <footer className="app-footer">
        TrackSentinel v1.0 · Railroad OT Cyber Defense Platform · Portfolio Demonstration
      </footer>
    </div>
  );
}

export default App;