function DashboardCards({ dashboard }) {
  if (!dashboard) return null;

  return (
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
  );
}

export default DashboardCards;