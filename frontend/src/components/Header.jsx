import "./Header.css";

function Header({ threatLevel }) {
  return (
    <header className="header">
      <div className="header-left">
        <button className="logo-box" type="button" aria-label="TrackSentinel home">
          <img src="/logo.png" alt="TrackSentinel Logo" />
        </button>

        <div>
          <h1>TrackSentinel</h1>

          <p className="subtitle">RailSOC Training & Simulation Platform</p>

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

  <strong
  className={
    threatLevel === "Critical"
      ? "header-status-critical"
      : threatLevel === "Elevated"
      ? "header-status-elevated"
      : "header-status-normal"
  }
>
  {threatLevel}
</strong>
</div>

        <div className="status-card">
          <span className="status-label">Platform</span>
          <strong>TrackSentinel v1.0</strong>
        </div>
      </div>
    </header>
  );
}

export default Header;