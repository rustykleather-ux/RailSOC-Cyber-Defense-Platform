function DemoControls({ simulateAttack, resetDemo }) {
  return (
    <>
      <h2>Rail Operations Simulation Console</h2>

      <p className="simulation-subtitle">
        Generate simulated Operational Technology security events for analyst
        training and incident response exercises.
      </p>

      <div className="attack-buttons">

        <button onClick={() => simulateAttack("inverter-offline")}>
          🚦 Signal Controller Communication Loss
        </button>

        <button onClick={() => simulateAttack("plc-firmware")}>
          ⚙️ Unauthorized Logic Modification
        </button>

        <button onClick={() => simulateAttack("failed-logins")}>
          👤 Unauthorized Engineering Login
        </button>

        <button onClick={() => simulateAttack("network-scan")}>
          📡 OT Network Reconnaissance
        </button>

        <button className="reset-button" onClick={resetDemo}>
          Restore Operational Baseline
        </button>

      </div>
    </>
  );
}

export default DemoControls;