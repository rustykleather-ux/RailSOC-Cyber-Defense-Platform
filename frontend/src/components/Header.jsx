import "./Header.css";

function Header() {
  return (
    <header className="header">
      <div className="header-left">
        <div className="logo-box">RS</div>

        <div>
          <h1>RailSOC</h1>

          <p className="subtitle">
            Railroad Operational Technology Security Operations Center
          </p>

          <p className="tagline">
            Monitoring • Detection • Incident Response • Threat Hunting
          </p>
        </div>
      </div>

      <div className="header-right">
        <div className="status-card">
          <span className="status-label">Environment</span>
          <strong>Simulation</strong>
        </div>

        <div className="status-card">
          <span className="status-label">Threat Level</span>
          <strong className="warning">Elevated</strong>
        </div>

        <div className="status-card">
          <span className="status-label">Platform</span>
          <strong>RailSOC v1.0</strong>
        </div>
      </div>
    </header>
  );
}

export default Header;