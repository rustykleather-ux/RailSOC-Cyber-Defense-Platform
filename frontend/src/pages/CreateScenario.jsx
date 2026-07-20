import { useEffect, useState } from "react";

function CreateScenario() {
  const [attacks, setAttacks] = useState([]);
  const [devices, setDevices] = useState([]);
  const [selectedAttack, setSelectedAttack] = useState("");
  const [selectedTargets, setSelectedTargets] = useState([]);
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadScenarioData();
  }, []);

  async function loadScenarioData() {
    try {
      setError("");

      const [attackResponse, deviceResponse] = await Promise.all([
        fetch("http://127.0.0.1:8000/attacks"),
        fetch("http://127.0.0.1:8000/devices"),
      ]);

      if (!attackResponse.ok || !deviceResponse.ok) {
        throw new Error("Unable to load attacks or devices.");
      }

      const attackData = await attackResponse.json();
      const deviceData = await deviceResponse.json();

      setAttacks(attackData.attacks ?? attackData);
      setDevices(deviceData.devices ?? deviceData);
    } catch (err) {
      setError(err.message);
    }
  }

  function toggleTarget(deviceId) {
    setSelectedTargets((currentTargets) => {
      if (currentTargets.includes(deviceId)) {
        return currentTargets.filter((id) => id !== deviceId);
      }

      return [...currentTargets, deviceId];
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!selectedAttack) {
      setError("Select an attack.");
      return;
    }

    if (selectedTargets.length === 0) {
      setError("Select at least one target device.");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setResult(null);

      const response = await fetch(
        "http://127.0.0.1:8000/training/custom-scenario",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            attack_id: selectedAttack,
            target_ids: selectedTargets,
            notes: notes || null,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Scenario launch failed.");
      }

      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="scenario-page">
      <section className="scenario-card">
        <h1>Create Custom Scenario</h1>
        <p>
          Select an attack type, choose target assets, and launch the
          simulation.
        </p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="attack">Attack Type</label>

          <select
            id="attack"
            value={selectedAttack}
            onChange={(event) => setSelectedAttack(event.target.value)}
          >
            <option value="">Select an attack</option>

            {attacks.map((attack) => (
              <option
                key={attack.id ?? attack.attack_id}
                value={attack.id ?? attack.attack_id}
              >
                {attack.name}
              </option>
            ))}
          </select>

          <fieldset>
            <legend>Target Devices</legend>

            {devices.map((device) => (
              <label key={device.id} className="target-option">
                <input
                  type="checkbox"
                  checked={selectedTargets.includes(device.id)}
                  onChange={() => toggleTarget(device.id)}
                />

                <span>
                  <strong>{device.name}</strong>
                  <small>
                    {device.device_type} — {device.status}
                  </small>
                </span>
              </label>
            ))}
          </fieldset>

          <label htmlFor="notes">Scenario Notes</label>

          <textarea
            id="notes"
            rows="5"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Describe the purpose of this simulation..."
          />

          <button type="submit" disabled={loading}>
            {loading ? "Launching..." : "Launch Scenario"}
          </button>
        </form>

        {error && <div className="scenario-error">{error}</div>}

        {result && (
          <section className="scenario-result">
            <h2>Scenario Launched</h2>

            <pre>{JSON.stringify(result, null, 2)}</pre>
          </section>
        )}
      </section>
    </main>
  );
}

export default CreateScenario;