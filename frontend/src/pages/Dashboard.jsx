import EnvironmentOverview from "../components/EnvironmentOverview";
import RailroadMap from "../components/RailroadMap";

function Dashboard({ dashboard, alerts, incidents, vulnerabilities, devices, trains, threatLevel }) {
  const recentIncidents = (incidents || []).slice(0, 3);
  const topAlerts = (alerts || []).slice(0, 3);
console.log("Dashboard trains:", trains);
  return (
    <>
      <EnvironmentOverview
        dashboard={dashboard}
        alerts={alerts}
        incidents={incidents}
        vulnerabilities={vulnerabilities}
        threatLevel={threatLevel}
      />

      

      <RailroadMap
        devices={devices}
        incidents={incidents}
        trains={trains}
      />

      <div className="dashboard-summary-grid">
        <section className="summary-panel">
          <h2>Recent Incidents</h2>

          {recentIncidents.length === 0 ? (
            <p className="muted">No open incidents.</p>
          ) : (
            recentIncidents.map((incident) => (
              <div className="summary-item" key={incident.id}>
                <span className={`badge ${(incident.severity || "low").toLowerCase()}`}>
                  {incident.severity}
                </span>
                <div>
                  <strong>{incident.alert_type || "Rail OT Incident"}</strong>
                  <p>{incident.device || "Unknown Rail Asset"}</p>
                </div>
              </div>
            ))
          )}
        </section>

        <section className="summary-panel">
          <h2>Top Active Alerts</h2>

          {topAlerts.length === 0 ? (
            <p className="muted">No active alerts.</p>
          ) : (
            topAlerts.map((alert) => (
              <div className="summary-item" key={alert.id}>
                <span className={`badge ${(alert.severity || "low").toLowerCase()}`}>
                  {alert.severity}
                </span>
                <div>
                  <strong>{alert.alert_type || "Security Alert"}</strong>
                  <p>{alert.device || "Unknown Rail Asset"}</p>
                </div>
              </div>
            ))
          )}
        </section>
      </div>
    </>
  );
}

export default Dashboard;