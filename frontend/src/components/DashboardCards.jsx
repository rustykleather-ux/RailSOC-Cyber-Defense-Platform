function DashboardCards({ dashboard }) {
  if (!dashboard) return null;

  return (
    <div className="cards">

      <div className="card">
        <span>Rail Assets</span>
        <strong>{dashboard.total_devices}</strong>
      </div>

      <div className="card">
        <span>Operational Assets</span>
        <strong>{dashboard.online_devices}</strong>
      </div>

      <div className="card warning">
        <span>Assets Requiring Attention</span>
        <strong>{dashboard.offline_devices}</strong>
      </div>

      <div className="card danger">
        <span>Critical Infrastructure Risk</span>
        <strong>{dashboard.high_risk_devices}</strong>
      </div>

      <div className="card danger">
        <span>Open Security Findings</span>
        <strong>{dashboard.open_vulnerabilities}</strong>
      </div>

    </div>
  );
}

export default DashboardCards;