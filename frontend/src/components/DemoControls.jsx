function DemoControls({ simulateAttack, resetDemo }) {
  return (
    <>
      <h2>Simulated Attack Engine</h2>

      <div className="attack-buttons">
        <button onClick={() => simulateAttack("inverter-offline")}>
          🔴 Inverter Offline
        </button>

        <button onClick={() => simulateAttack("plc-firmware")}>
          ⚠️ PLC Firmware Change
        </button>

        <button onClick={() => simulateAttack("failed-logins")}>
          🔑 Failed Logins
        </button>

        <button onClick={() => simulateAttack("network-scan")}>
          🌐 Network Scan
        </button>

        <button className="reset-button" onClick={resetDemo}>
          Reset Demo Baseline
        </button>
      </div>
    </>
  );
}

export default DemoControls;