function RecentScenarioActivity({ alerts = [] }) {
  const recentActivity = [...alerts]
    .sort((a, b) => {
      const timeA = new Date(
        a.timestamp || a.time || a.created_at || 0
      ).getTime();

      const timeB = new Date(
        b.timestamp || b.time || b.created_at || 0
      ).getTime();

      return timeB - timeA;
    })
    .slice(0, 5);

  function formatTime(value) {
    if (!value) {
      return "Time unavailable";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return "Time unavailable";
    }

    return date.toLocaleTimeString([], {
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function getSeverityClass(severity) {
    return String(severity || "low").toLowerCase();
  }

  return (
    <section className="recent-scenario-panel">
      <div className="recent-scenario-header">
        <div>
          <p className="scenario-eyebrow">
            Training and Security Events
          </p>

          <h2>Recent Scenario Activity</h2>
        </div>

        <span className="recent-scenario-count">
          {recentActivity.length} recent
        </span>
      </div>

      {recentActivity.length === 0 ? (
        <div className="recent-scenario-empty">
          <p>No recent scenario activity.</p>
          <span>
            Launch a training scenario to generate activity.
          </span>
        </div>
      ) : (
        <div className="recent-scenario-list">
          {recentActivity.map((alert, index) => {
            const timestamp =
              alert.timestamp ||
              alert.time ||
              alert.created_at;

            return (
              <article
                className="recent-scenario-item"
                key={alert.id || `${alert.alert_type}-${index}`}
              >
                <div className="recent-scenario-time">
                  <span>{formatTime(timestamp)}</span>

                  <div
                    className={`activity-marker ${getSeverityClass(
                      alert.severity
                    )}`}
                    aria-hidden="true"
                  />
                </div>

                <div className="recent-scenario-content">
                  <div className="recent-scenario-title-row">
                    <strong>
                      {alert.alert_type || "Security Activity"}
                    </strong>

                    <span
                      className={`badge ${getSeverityClass(
                        alert.severity
                      )}`}
                    >
                      {alert.severity || "Low"}
                    </span>
                  </div>

                  <p className="recent-scenario-asset">
                    {alert.device ||
                      alert.device_name ||
                      alert.asset_name ||
                      "Unknown Rail Asset"}
                  </p>

                  {alert.message && (
                    <p className="recent-scenario-message">
                      {alert.message}
                    </p>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default RecentScenarioActivity;