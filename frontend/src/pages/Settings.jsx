function Settings() {
  return (
    <section className="settings-page">
      <div className="settings-header">
        <h2>Platform Settings</h2>
        <p>
          Configure the TrackSentinel simulation environment and platform
          preferences.
        </p>
      </div>

      <div className="settings-grid">
        <div className="settings-card">
          <h3>Platform</h3>

          <label>Mode</label>
          <select defaultValue="Simulation">
            <option>Simulation</option>
            <option disabled>Production (Future)</option>
          </select>

          <label>Theme</label>
          <select defaultValue="Dark SOC">
            <option>Dark SOC</option>
            <option>Light</option>
          </select>

          <label>Auto Refresh</label>
          <select defaultValue="3">
            <option value="3">Every 3 seconds</option>
            <option value="5">Every 5 seconds</option>
            <option value="10">Every 10 seconds</option>
          </select>
        </div>

        <div className="settings-card">
          <h3>Threat Detection</h3>

          <label>
            <input type="checkbox" defaultChecked />
            Enable Attack Simulation
          </label>

          <label>
            <input type="checkbox" defaultChecked />
            Generate Demo Alerts
          </label>

          <label>
            <input type="checkbox" defaultChecked />
            Dynamic Threat Level
          </label>

          <label>
            <input type="checkbox" defaultChecked />
            MITRE ATT&CK Mapping
          </label>
        </div>

        <div className="settings-card">
          <h3>Data Sources</h3>

          <table className="settings-table">
            <tbody>
              <tr>
                <td>Backend</td>
                <td>FastAPI</td>
              </tr>

              <tr>
                <td>Database</td>
                <td>SQLite</td>
              </tr>

              <tr>
                <td>Frontend</td>
                <td>React + Vite</td>
              </tr>

              <tr>
                <td>Telemetry</td>
                <td>Simulation Engine</td>
              </tr>

              <tr>
                <td>Version</td>
                <td>TrackSentinel v1.0</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="settings-card">
          <h3>Future Enterprise Features</h3>

          <ul>
            <li>✓ Active Directory Authentication</li>
            <li>✓ Role-Based Access Control (RBAC)</li>
            <li>✓ Splunk / Microsoft Sentinel Integration</li>
            <li>✓ Syslog Collection</li>
            <li>✓ CISA KEV Synchronization</li>
            <li>✓ Dragos / Nozomi Integration</li>
            <li>✓ Multi-Site Railroad Monitoring</li>
          </ul>
        </div>
      </div>

      <div className="settings-footer">
        <button className="primary-button">
          Save Configuration
        </button>

        <button className="secondary-button">
          Restore Defaults
        </button>
      </div>
    </section>
  );
}

export default Settings;