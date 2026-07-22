import "./ScenarioResultsDrawer.css";

function ScenarioResultsDrawer({
  result,
  onClose,
}) {
  if (!result) {
    return null;
  }

  const scenario = result.scenario || {};
  const simulationResults = Array.isArray(result.simulation)
    ? result.simulation
    : [];

  const severityClass = (
    scenario.severity || "low"
  ).toLowerCase();

  return (
    <div
      className="scenario-drawer-overlay"
      onClick={onClose}
    >
      <aside
        className="scenario-results-drawer"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="scenario-results-header">
          <div>
            <span className="section-eyebrow">
              Scenario Execution
            </span>

            <h2>Scenario Results</h2>
          </div>

          <button
            type="button"
            className="drawer-close-button"
            onClick={onClose}
            aria-label="Close scenario results"
          >
            ×
          </button>
        </div>

        <div className="scenario-results-summary">
          <div>
            <span className="result-label">
              Attack
            </span>

            <strong>
              {scenario.attack_name ||
                "Custom Scenario"}
            </strong>
          </div>

          <span
            className={`badge ${severityClass}`}
          >
            {scenario.severity || "Unknown"}
          </span>
        </div>

        <div className="scenario-result-grid">
          <div className="scenario-result-card">
            <span className="result-label">
              Status
            </span>

            <strong>
              {scenario.status || "Unknown"}
            </strong>
          </div>

          <div className="scenario-result-card">
            <span className="result-label">
              MITRE ATT&CK
            </span>

            <strong>
              {scenario.mitre_id || "Not mapped"}
            </strong>

            <p>
              {scenario.mitre_name || ""}
            </p>
          </div>
        </div>

        <section className="scenario-results-section">
          <h3>Targets</h3>

          {Array.isArray(scenario.target_names) &&
          scenario.target_names.length > 0 ? (
            <ul className="scenario-target-list">
              {scenario.target_names.map(
                (targetName) => (
                  <li key={targetName}>
                    {targetName}
                  </li>
                )
              )}
            </ul>
          ) : (
            <p className="muted">
              No targets returned.
            </p>
          )}
        </section>

        <section className="scenario-results-section">
          <h3>Simulation Results</h3>

          {simulationResults.length === 0 ? (
            <p className="muted">
              No simulation details returned.
            </p>
          ) : (
            <div className="simulation-result-list">
              {simulationResults.map(
                (simulation, index) => (
                  <article
                    className="simulation-result-item"
                    key={
                      simulation.device_id ||
                      `${simulation.device_name}-${index}`
                    }
                  >
                    <div className="result-success-icon">
                      ✓
                    </div>

                    <div>
                      <strong>
                        {simulation.device_name ||
                          "Railroad Asset"}
                      </strong>

                      <p>
                        Status changed from{" "}
                        <span>
                          {simulation.previous_status ||
                            "Unknown"}
                        </span>{" "}
                        to{" "}
                        <span>
                          {simulation.new_status ||
                            "Unknown"}
                        </span>
                      </p>

                      {simulation.alert_type && (
                        <div className="result-alert-detail">
                          <span
                            className={`badge ${(
                              simulation.alert_severity ||
                              "low"
                            ).toLowerCase()}`}
                          >
                            {simulation.alert_severity ||
                              "Alert"}
                          </span>

                          <span>
                            {simulation.alert_type}
                          </span>
                        </div>
                      )}

                      {simulation.detected_condition && (
                        <p className="detected-condition">
                          Detected condition:{" "}
                          {
                            simulation.detected_condition
                          }
                        </p>
                      )}
                    </div>
                  </article>
                )
              )}
            </div>
          )}
        </section>

        {scenario.notes && (
          <section className="scenario-results-section">
            <h3>Scenario Notes</h3>

            <p>{scenario.notes}</p>
          </section>
        )}

        <div className="scenario-results-actions">
          <button
            type="button"
            className="primary-button"
            onClick={onClose}
          >
            Return to Scenario Builder
          </button>
        </div>
      </aside>
    </div>
  );
}

export default ScenarioResultsDrawer;