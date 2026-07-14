import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  NavLink,
} from "react-router-dom";
import "./App.css";

import InvestigationWorkspace from "./pages/InvestigationWorkspace";
import ExecutiveDashboard from "./pages/ExecutiveDashboard";
import IncidentTimeline from "./pages/IncidentTimeline";
import Header from "./components/Header";
import ThreatIntel from "./pages/ThreatIntel";
import Dashboard from "./pages/Dashboard";
import Assets from "./pages/Assets";
import Alerts from "./pages/Alerts";
import Incidents from "./pages/Incidents";
import Topology from "./pages/Topology";
import Telemetry from "./pages/Telemetry";
import Training from "./pages/Training";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";
import Vulnerabilities from "./pages/Vulnerabilities";

import { getTrains } from "./services/trainService";
import { getTrackBlocks } from "./services/blockService";

import {
  getIncidents,
  acknowledgeIncidentRequest,
  assignIncidentRequest,
  updateIncidentNotesRequest,
  closeIncidentRequest,
} from "./services/incidentService";

import {
  LayoutDashboard,
  Target,
  Network,
  RadioTower,
  TriangleAlert,
  Brain,
  Clock3,
  ClipboardList,
  Search,
  TrafficCone,
  ShieldAlert,
  ChartNoAxesCombined,
  FileChartColumn,
  Settings as SettingsIcon,
} from "lucide-react";

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
  const [trains, setTrains] = useState([]);
  const [trackBlocks, setTrackBlocks] = useState([]);

  const loadPlantStatus = async () => {
    try {
      const response = await getPlantStatus();

      setPlantStatus(
        Array.isArray(response.data)
          ? response.data
          : []
      );
    } catch (err) {
      console.error(
        "TrackSentinel Telemetry Error:",
        err
      );
    }
  };

  const loadTrains = async () => {
    try {
      const data = await getTrains();

      setTrains(
        Array.isArray(data)
          ? data
          : []
      );
    } catch (err) {
      console.error(
        "TrackSentinel Train Load Error:",
        err
      );
    }
  };

  const loadTrackBlocks = async () => {
    try {
      const data = await getTrackBlocks();

      setTrackBlocks(
        Array.isArray(data)
          ? data
          : []
      );
    } catch (err) {
      console.error(
        "TrackSentinel Track Block Error:",
        err
      );
    }
  };

  const loadData = async () => {
    try {
      const [
        devicesRes,
        vulnerabilitiesRes,
        dashboardRes,
        alertsRes,
        incidentsRes,
        trainsRes,
        trackBlocksRes,
        plantStatusRes,
      ] = await Promise.all([
        getDevices(),
        getVulnerabilities(),
        getDashboard(),
        getAlerts(),
        getIncidents(),
        getTrains(),
        getTrackBlocks(),
        getPlantStatus(),
      ]);

      setDevices(
        Array.isArray(devicesRes.data)
          ? devicesRes.data
          : []
      );

      setVulnerabilities(
        Array.isArray(vulnerabilitiesRes.data)
          ? vulnerabilitiesRes.data
          : []
      );

      setDashboard(
        dashboardRes.data || null
      );

      setAlerts(
        Array.isArray(alertsRes.data)
          ? alertsRes.data
          : []
      );

      setIncidents(
        Array.isArray(incidentsRes.data)
          ? incidentsRes.data
          : []
      );

      setTrains(
        Array.isArray(trainsRes)
          ? trainsRes
          : []
      );

      setTrackBlocks(
        Array.isArray(trackBlocksRes)
          ? trackBlocksRes
          : []
      );

      setPlantStatus(
        Array.isArray(plantStatusRes.data)
          ? plantStatusRes.data
          : []
      );
    } catch (err) {
      console.error(
        "TrackSentinel Load Data Error:",
        err
      );
    }
  };

  useEffect(() => {
    loadData();

    const intervalId = window.setInterval(() => {
      loadPlantStatus();
      loadTrains();
      loadTrackBlocks();
    }, 3000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, []);

  const simulateAttack = async (attackType) => {
    try {
      await simulateAttackRequest(attackType);
      await loadData();
    } catch (err) {
      console.error(
        "TrackSentinel Simulation Error:",
        err
      );
    }
  };

  const resetDemo = async () => {
    try {
      await resetDemoRequest();
      await loadData();
    } catch (err) {
      console.error(
        "TrackSentinel Reset Error:",
        err
      );
    }
  };

  const acknowledgeIncident = async (incidentId) => {
    try {
      await acknowledgeIncidentRequest(incidentId);
      await loadData();
    } catch (err) {
      console.error(
        "Incident acknowledgement failed:",
        err
      );
    }
  };

  const assignIncident = async (
    incidentId,
    assignedTo
  ) => {
    try {
      await assignIncidentRequest(
        incidentId,
        assignedTo
      );

      await loadData();
    } catch (err) {
      console.error(
        "Incident assignment failed:",
        err
      );
    }
  };

  const updateIncidentNotes = async (
    incidentId,
    notes
  ) => {
    try {
      await updateIncidentNotesRequest(
        incidentId,
        notes
      );

      await loadData();
    } catch (err) {
      console.error(
        "Incident notes update failed:",
        err
      );
    }
  };

  const closeIncident = async (
    incidentId,
    closedBy
  ) => {
    try {
      await closeIncidentRequest(
        incidentId,
        closedBy
      );

      await loadData();
    } catch (err) {
      console.error(
        "Incident closure failed:",
        err
      );
    }
  };

  const criticalAlerts = alerts.filter(
    (alert) => alert.severity === "Critical"
  ).length;

  const highAlerts = alerts.filter(
    (alert) => alert.severity === "High"
  ).length;

  const openIncidents = incidents.filter(
    (incident) => incident.status !== "Closed"
  ).length;

  const offlineAssets =
    dashboard?.offline_devices || 0;

  const highRiskAssets =
    dashboard?.high_risk_devices || 0;

  let threatLevel = "Normal";

  if (
    criticalAlerts > 0 ||
    openIncidents > 0
  ) {
    threatLevel = "Critical";
  } else if (
    highAlerts > 0 ||
    offlineAssets > 0 ||
    highRiskAssets > 0
  ) {
    threatLevel = "Elevated";
  }

  return (
    <BrowserRouter>
      <div className="app-shell">
        <aside className="sidebar">
          <div className="sidebar-brand">
            <img
              src="/logo.png"
              alt="TrackSentinel"
            />

            <div>
              <strong>TrackSentinel</strong>
              <span>RailSOC Platform</span>
            </div>
          </div>

          <nav className="sidebar-nav">
            <NavLink to="/">
              <LayoutDashboard size={18} />
              <span>Dashboard</span>
            </NavLink>

            <NavLink to="/training">
              <Target size={18} />
              <span>Training Exercises</span>
            </NavLink>

            <NavLink to="/topology">
              <Network size={18} />
              <span>Railroad Topology</span>
            </NavLink>

            <NavLink to="/telemetry">
              <RadioTower size={18} />
              <span>Live Telemetry</span>
            </NavLink>

            <NavLink to="/alerts">
              <TriangleAlert size={18} />
              <span>Security Alerts</span>
            </NavLink>

            <NavLink to="/threat-intel">
              <Brain size={18} />
              <span>Threat Intelligence</span>
            </NavLink>

            <NavLink to="/timeline">
              <Clock3 size={18} />
              <span>Incident Timeline</span>
            </NavLink>

            <NavLink to="/incidents">
              <ClipboardList size={18} />
              <span>Incident Center</span>
            </NavLink>

            <NavLink to="/investigation">
              <Search size={18} />
              <span>Investigation</span>
            </NavLink>

            <NavLink to="/assets">
              <TrafficCone size={18} />
              <span>OT Assets</span>
            </NavLink>

            <NavLink to="/vulnerabilities">
              <ShieldAlert size={18} />
              <span>Vulnerabilities</span>
            </NavLink>

            <NavLink to="/executive">
              <ChartNoAxesCombined size={18} />
              <span>Executive Dashboard</span>
            </NavLink>

            <NavLink to="/reports">
              <FileChartColumn size={18} />
              <span>Reports</span>
            </NavLink>

            <NavLink to="/settings">
              <SettingsIcon size={18} />
              <span>Settings</span>
            </NavLink>
          </nav>
        </aside>

        <div className="app-content">
          <Header threatLevel={threatLevel} />

          <main className="railsoc-main">
            <Routes>
              <Route
                path="/"
                element={
                  <Dashboard
                    dashboard={dashboard}
                    alerts={alerts}
                    incidents={incidents}
                    vulnerabilities={vulnerabilities}
                    devices={devices}
                    trains={trains}
                    trackBlocks={trackBlocks}
                    threatLevel={threatLevel}
                  />
                }
              />

              <Route
                path="/executive"
                element={
                  <ExecutiveDashboard
                    dashboard={dashboard}
                    alerts={alerts}
                    incidents={incidents}
                    vulnerabilities={vulnerabilities}
                    threatLevel={threatLevel}
                  />
                }
              />

              <Route
                path="/timeline"
                element={
                  <IncidentTimeline
                    incidents={incidents}
                  />
                }
              />

              <Route
                path="/reports"
                element={
                  <Reports
                    dashboard={dashboard}
                    alerts={alerts}
                    incidents={incidents}
                    vulnerabilities={vulnerabilities}
                    threatLevel={threatLevel}
                  />
                }
              />

              <Route
                path="/training"
                element={
                  <Training
                    simulateAttack={simulateAttack}
                    resetDemo={resetDemo}
                  />
                }
              />

              <Route
                path="/investigation"
                element={
                  <InvestigationWorkspace
                    incidents={incidents}
                  />
                }
              />

              <Route
                path="/topology"
                element={
                  <Topology
                    devices={devices}
                  />
                }
              />

              <Route
                path="/telemetry"
                element={
                  <Telemetry
                    plantStatus={plantStatus}
                  />
                }
              />

              <Route
                path="/alerts"
                element={
                  <Alerts alerts={alerts} />
                }
              />

              <Route
                path="/incidents"
                element={
                  <Incidents
                    incidents={incidents}
                    acknowledgeIncident={
                      acknowledgeIncident
                    }
                    assignIncident={
                      assignIncident
                    }
                    updateIncidentNotes={
                      updateIncidentNotes
                    }
                    closeIncident={
                      closeIncident
                    }
                  />
                }
              />

              <Route
                path="/threat-intel"
                element={
                  <ThreatIntel
                    threatLevel={threatLevel}
                    alerts={alerts}
                    incidents={incidents}
                    vulnerabilities={vulnerabilities}
                  />
                }
              />

              <Route
                path="/assets"
                element={
                  <Assets devices={devices} />
                }
              />

              <Route
                path="/vulnerabilities"
                element={
                  <Vulnerabilities
                    vulnerabilities={
                      vulnerabilities
                    }
                  />
                }
              />

              <Route
                path="/settings"
                element={<Settings />}
              />
            </Routes>

            <footer className="app-footer">
              TrackSentinel v1.0 · Railroad OT Cyber
              Defense Platform · Portfolio Demonstration
            </footer>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;