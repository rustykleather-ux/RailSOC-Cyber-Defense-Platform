import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import "./App.css";

import Header from "./components/Header";

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
    const interval = setInterval(loadPlantStatus, 3000);
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
    await acknowledgeIncidentRequest(incidentId);
    await loadData();
  };

  const assignIncident = async (incidentId, assignedTo) => {
    await assignIncidentRequest(incidentId, assignedTo);
    await loadData();
  };

  const updateIncidentNotes = async (incidentId, notes) => {
    await updateIncidentNotesRequest(incidentId, notes);
    await loadData();
  };

  const closeIncident = async (incidentId, closedBy) => {
    await closeIncidentRequest(incidentId, closedBy);
    await loadData();
  };

  return (
    <BrowserRouter>
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
            <NavLink to="/">📊 Dashboard</NavLink>
            <NavLink to="/training">🎯 Training Exercises</NavLink>
            <NavLink to="/topology">🛤 Railroad Topology</NavLink>
            <NavLink to="/telemetry">📡 Live Telemetry</NavLink>
            <NavLink to="/alerts">🚨 Security Alerts</NavLink>
            <NavLink to="/incidents">📝 Incident Center</NavLink>
            <NavLink to="/assets">🚦 OT Assets</NavLink>
            <NavLink to="/vulnerabilities">⚠️ Vulnerabilities</NavLink>
            <NavLink to="/reports">📈 Reports</NavLink>
            <NavLink to="/settings">⚙️ Settings</NavLink>
          </nav>
        </aside>

        <div className="app-content">
          <Header />

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
                path="/topology"
                element={<Topology devices={devices} />}
              />

              <Route
                path="/telemetry"
                element={<Telemetry plantStatus={plantStatus} />}
              />

              <Route
                path="/alerts"
                element={<Alerts alerts={alerts} />}
              />

              <Route
                path="/incidents"
                element={
                  <Incidents
                    incidents={incidents}
                    acknowledgeIncident={acknowledgeIncident}
                    assignIncident={assignIncident}
                    updateIncidentNotes={updateIncidentNotes}
                    closeIncident={closeIncident}
                  />
                }
              />

              <Route
                path="/assets"
                element={<Assets devices={devices} />}
              />

              <Route
                path="/vulnerabilities"
                element={<Vulnerabilities vulnerabilities={vulnerabilities} />}
              />

              <Route path="/reports" element={<Reports />} />

              <Route path="/settings" element={<Settings />} />
            </Routes>

            <footer className="app-footer">
              TrackSentinel v1.0 · Railroad OT Cyber Defense Platform · Portfolio Demonstration
            </footer>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;