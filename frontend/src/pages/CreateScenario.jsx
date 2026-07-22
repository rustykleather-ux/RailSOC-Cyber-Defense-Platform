import { useEffect, useMemo, useState } from "react";
import ScenarioResultsDrawer from "../components/ScenarioResultsDrawer";


function CreateScenario() {
  const [attacks, setAttacks] = useState([]);
  const [devices, setDevices] = useState([]);
  const [selectedAttack, setSelectedAttack] = useState("");
  const [selectedTargets, setSelectedTargets] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [dataLoading, setDataLoading] = useState(true);
  const [scenarioResult, setScenarioResult] = useState(null);
  

  useEffect(() => {
    loadScenarioData();
  }, []);

  async function loadScenarioData() {
    try {
      setDataLoading(true);
      setError("");

      const [attackResponse, deviceResponse] = await Promise.all([
        fetch("http://127.0.0.1:8000/attacks"),
        fetch("http://127.0.0.1:8000/devices"),
      ]);

      if (!attackResponse.ok) {
        throw new Error(
          `Unable to load attacks. Server returned ${attackResponse.status}.`
        );
      }

      if (!deviceResponse.ok) {
        throw new Error(
          `Unable to load devices. Server returned ${deviceResponse.status}.`
        );
      }

      const attackData = await attackResponse.json();
      const deviceData = await deviceResponse.json();

      setAttacks(
        Array.isArray(attackData?.attacks)
          ? attackData.attacks
          : Array.isArray(attackData)
          ? attackData
          : []
      );

      setDevices(
        Array.isArray(deviceData?.devices)
          ? deviceData.devices
          : Array.isArray(deviceData)
          ? deviceData
          : []
      );
    } catch (err) {
      setError(err.message || "Unable to load scenario data.");
    } finally {
      setDataLoading(false);
    }
  }

  function normalizeAssetType(value) {
    return String(value ?? "")
      .trim()
      .toLowerCase()
      .replaceAll("-", " ")
      .replaceAll("_", " ");
  }

  const selectedAttackDetails = useMemo(() => {
    return attacks.find(
      (attack) =>
        String(attack.id ?? attack.attack_id) === String(selectedAttack)
    );
  }, [attacks, selectedAttack]);

  const compatibleTypes = useMemo(() => {
    return (
      selectedAttackDetails?.compatible_types?.map((type) =>
        normalizeAssetType(type)
      ) ?? []
    );
  }, [selectedAttackDetails]);

  const filteredDevices = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();

    return devices.filter((device) => {
      const deviceType = normalizeAssetType(
        device.device_type ?? device.type ?? ""
      );

      const isCompatible =
        compatibleTypes.length === 0 ||
        compatibleTypes.includes(deviceType);

      const searchableText = [
        device.name,
        device.device_type,
        device.type,
        device.location,
        device.status,
        device.ip_address,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesSearch =
        normalizedSearch === "" ||
        searchableText.includes(normalizedSearch);

      return isCompatible && matchesSearch;
    });
  }, [devices, compatibleTypes, searchTerm]);

  const selectedDeviceDetails = useMemo(() => {
    return devices.filter((device) =>
      selectedTargets.some(
        (selectedId) => String(selectedId) === String(device.id)
      )
    );
  }, [devices, selectedTargets]);

  function toggleTarget(deviceId) {
    setSelectedTargets((currentTargets) => {
      const isSelected = currentTargets.some(
        (selectedId) => String(selectedId) === String(deviceId)
      );

      if (isSelected) {
        return currentTargets.filter(
          (selectedId) => String(selectedId) !== String(deviceId)
        );
      }

      return [...currentTargets, deviceId];
    });

    setResult(null);
    setError("");
  }

  function handleAttackChange(event) {
    const attackId = event.target.value;

    setSelectedAttack(attackId);
    setSelectedTargets([]);
    setSearchTerm("");
    setResult(null);
    setError("");
  }

  function clearTargets() {
    setSelectedTargets([]);
    setResult(null);
  }

  function getStatusClass(status) {
    const normalizedStatus = String(status ?? "").toLowerCase();

    if (
      normalizedStatus.includes("compromised") ||
      normalizedStatus.includes("offline") ||
      normalizedStatus.includes("critical")
    ) {
      return "status-critical";
    }

    if (
      normalizedStatus.includes("degraded") ||
      normalizedStatus.includes("maintenance") ||
      normalizedStatus.includes("warning")
    ) {
      return "status-warning";
    }

    return "status-healthy";
  }

  function getImpactClass(status) {
    const normalizedStatus = String(status ?? "").toLowerCase();

    if (
      normalizedStatus.includes("offline") ||
      normalizedStatus.includes("compromised") ||
      normalizedStatus.includes("critical") ||
      normalizedStatus.includes("encrypted")
    ) {
      return "impact-critical";
    }

    if (
      normalizedStatus.includes("degraded") ||
      normalizedStatus.includes("maintenance") ||
      normalizedStatus.includes("warning") ||
      normalizedStatus.includes("unstable")
    ) {
      return "impact-warning";
    }

    return "impact-operational";
  }

  function getAssetIcon(deviceType) {
    const type = normalizeAssetType(deviceType);

    if (type.includes("signal")) return "🚦";
    if (type.includes("switch")) return "🔀";
    if (type.includes("server")) return "🖥️";
    if (type.includes("workstation")) return "💻";
    if (type.includes("network")) return "🌐";
    if (type.includes("gateway")) return "📡";
    if (type.includes("radio")) return "📡";
    if (type.includes("access control")) return "🚪";
    if (type.includes("iot")) return "📟";
    if (type.includes("plc")) return "⚙️";
    if (type.includes("controller")) return "⚙️";
    if (type.includes("sensor")) return "📟";

    return "🛡️";
  }

  function getOperatorAction(attack) {
    const attackId = attack?.id ?? attack?.attack_id;

    const actions = {
      logic_modification:
        "Validate controller logic against the approved baseline, isolate unauthorized engineering access, and restore the trusted configuration.",

      credential_abuse:
        "Review authentication logs, disable or reset affected accounts, terminate suspicious sessions, and verify privilege assignments.",

      network_recon:
        "Review network telemetry, identify the scanning source, validate segmentation controls, and determine whether reconnaissance progressed further.",

      firmware_tampering:
        "Isolate the affected controller, verify firmware integrity, compare it against the approved version, and restore trusted firmware.",

      denial_of_service:
        "Confirm service impact, identify the traffic source, apply containment controls, and restore critical railroad services.",

      communication_failure:
        "Check communication paths, validate network and field-device connectivity, inspect affected links, and restore communications.",

      malware_injection:
        "Isolate the affected endpoint, preserve evidence, inspect active processes and persistence mechanisms, and begin malware containment procedures.",

      ransomware_attack:
        "Immediately isolate the affected system, protect backups, preserve evidence, and activate the ransomware response plan.",

      sensor_tampering:
        "Compare sensor readings against trusted sources, inspect the sensor and controller path, and restore validated telemetry.",

      power_fluctuation:
        "Inspect power quality and backup systems, validate device stability, and determine whether the event is physical or cyber-induced.",

      brute_force_attack:
        "Identify the source of failed authentication attempts, lock or protect targeted accounts, and review access-control policies.",

      data_exfiltration:
        "Contain outbound communication, identify transferred data, preserve logs, and investigate the affected account and endpoint.",

      door_access:
        "Validate physical access records, review badge use and camera footage, and secure the affected restricted area.",
    };

    return (
      actions[attackId] ??
      "Investigate the affected asset, validate the alert, contain the activity, and restore normal railroad operations."
    );
  }

  function getExpectedStatus(attack, currentStatus = "Operational") {
    return (
      attack?.simulation_effect?.status ??
      attack?.simulation_effect?.device_status ??
      currentStatus
    );
  }

  function isAlreadyAffected(status) {
    const normalizedStatus = String(status ?? "").toLowerCase();

    return [
      "compromised",
      "offline",
      "degraded",
      "critical",
      "encrypted",
    ].some((condition) => normalizedStatus.includes(condition));
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
            notes: notes.trim() || null,
          }),
        }
      );

      let data;

      try {
        data = await response.json();
      } catch {
        data = null;
      }

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            data?.message ||
            `Scenario launch failed. Server returned ${response.status}.`
        );
      }

      const resultData =
        data ?? {
          message: "Scenario launched successfully.",
        };

      setResult(resultData);
      setScenarioResult(resultData);
    } catch (err) {
      setError(resultData);
      setScenarioResult(resultData)
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="scenario-page">
      <section className="scenario-card">
        <div className="scenario-header">
          <div>
            <p className="scenario-eyebrow">Training Environment</p>

            <h1>Create Custom Scenario</h1>

            <p>
              Select an attack type, choose compatible railroad assets, and
              launch the simulation.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="scenario-form-section">
            <label htmlFor="attack">Attack Type</label>

            <select
              id="attack"
              value={selectedAttack}
              onChange={handleAttackChange}
              disabled={dataLoading || loading}
            >
              <option value="">
                {dataLoading
                  ? "Loading attacks..."
                  : "Select an attack"}
              </option>

              {attacks.map((attack) => {
                const attackId = attack.id ?? attack.attack_id;

                return (
                  <option key={attackId} value={attackId}>
                    {attack.name}
                  </option>
                );
              })}
            </select>
          </div>

          {selectedAttackDetails && (
            <section className="attack-summary">
              <div className="attack-summary-heading">
                <div>
                  <span className="attack-summary-label">
                    Selected attack
                  </span>

                  <h2>{selectedAttackDetails.name}</h2>
                </div>

                <span
                  className={`severity-badge severity-${String(
                    selectedAttackDetails.severity ?? "unknown"
                  ).toLowerCase()}`}
                >
                  {selectedAttackDetails.severity ?? "Unknown"}
                </span>
              </div>

              <p>
                {selectedAttackDetails.description ??
                  "No attack description is available."}
              </p>

              <div className="attack-summary-meta">
                {selectedAttackDetails.mitre_id && (
                  <span>
                    <strong>MITRE:</strong>{" "}
                    {selectedAttackDetails.mitre_id}
                    {selectedAttackDetails.mitre_name
                      ? ` — ${selectedAttackDetails.mitre_name}`
                      : ""}
                  </span>
                )}

                {compatibleTypes.length > 0 && (
                  <span>
                    <strong>Compatible assets:</strong>{" "}
                    {selectedAttackDetails.compatible_types.join(", ")}
                  </span>
                )}
              </div>
            </section>
          )}

          {selectedAttackDetails && (
            <section className="scenario-intelligence-panel">
              <div className="scenario-intelligence-header">
                <div>
                  <p className="scenario-intelligence-eyebrow">
                    Scenario Intelligence
                  </p>

                  <h2>Expected Operational Impact</h2>
                </div>

                <span
                  className={`impact-status-badge ${getImpactClass(
                    getExpectedStatus(
                      selectedAttackDetails,
                      "No Status Change"
                    )
                  )}`}
                >
                  {getExpectedStatus(
                    selectedAttackDetails,
                    "No Status Change"
                  )}
                </span>
              </div>

              <div className="scenario-intelligence-grid">
                <article className="intelligence-item">
                  <span
                    className="intelligence-icon"
                    aria-hidden="true"
                  >
                    ⚠️
                  </span>

                  <div>
                    <h3>Detection Condition</h3>

                    <p>
                      {selectedAttackDetails.condition ??
                        "No detection condition defined."}
                    </p>
                  </div>
                </article>

                <article className="intelligence-item">
                  <span
                    className="intelligence-icon"
                    aria-hidden="true"
                  >
                    📉
                  </span>

                  <div>
                    <h3>Expected Effect</h3>

                    <p>
                      Asset status changes to{" "}
                      <strong>
                        {getExpectedStatus(
                          selectedAttackDetails,
                          "Operational"
                        )}
                      </strong>
                      .
                    </p>
                  </div>
                </article>

                <article className="intelligence-item intelligence-item-wide">
                  <span
                    className="intelligence-icon"
                    aria-hidden="true"
                  >
                    👤
                  </span>

                  <div>
                    <h3>Recommended Operator Action</h3>

                    <p>
                      {getOperatorAction(selectedAttackDetails)}
                    </p>
                  </div>
                </article>
              </div>
            </section>
          )}

          <section className="target-section">
            <div className="target-section-heading">
              <div>
                <h2>Target Assets</h2>

                <p>
                  Select one or more assets to include in the training
                  scenario.
                </p>
              </div>

              <div className="target-selection-summary">
                <span>{selectedTargets.length} selected</span>

                {selectedTargets.length > 0 && (
                  <button
                    type="button"
                    className="clear-selection-button"
                    onClick={clearTargets}
                    disabled={loading}
                  >
                    Clear selection
                  </button>
                )}
              </div>
            </div>

            <div className="asset-search-wrapper">
              <span className="asset-search-icon" aria-hidden="true">
                🔍
              </span>

              <input
                type="search"
                className="asset-search"
                value={searchTerm}
                onChange={(event) =>
                  setSearchTerm(event.target.value)
                }
                placeholder="Search by asset name, type, location, or status..."
                aria-label="Search target assets"
                disabled={!selectedAttack || dataLoading || loading}
              />
            </div>

            {dataLoading ? (
              <div className="asset-empty-state">
                Loading available assets...
              </div>
            ) : !selectedAttack ? (
              <div className="asset-empty-state">
                Select an attack to view compatible target assets.
              </div>
            ) : filteredDevices.length === 0 ? (
              <div className="asset-empty-state">
                No compatible assets match your search.
              </div>
            ) : (
              <>
                <div className="asset-grid-header">
                  <span>
                    {filteredDevices.length} compatible{" "}
                    {filteredDevices.length === 1
                      ? "asset"
                      : "assets"}
                  </span>
                </div>

                <div className="asset-card-grid">
                  {filteredDevices.map((device) => {
                    const isSelected = selectedTargets.some(
                      (selectedId) =>
                        String(selectedId) === String(device.id)
                    );

                    const deviceType =
                      device.device_type ??
                      device.type ??
                      "Unknown Asset";

                    return (
                      <button
                        key={device.id}
                        type="button"
                        className={`asset-selection-card ${
                          isSelected ? "selected" : ""
                        }`}
                        onClick={() => toggleTarget(device.id)}
                        aria-pressed={isSelected}
                        disabled={loading}
                      >
                        <div className="asset-card-top">
                          <span
                            className="asset-icon"
                            aria-hidden="true"
                          >
                            {getAssetIcon(deviceType)}
                          </span>

                          <span
                            className={`asset-status ${getStatusClass(
                              device.status
                            )}`}
                          >
                            {device.status ?? "Unknown"}
                          </span>
                        </div>

                        <div className="asset-card-content">
                          <h3>{device.name}</h3>

                          <p className="asset-type">
                            {deviceType}
                          </p>

                          {device.location && (
                            <p className="asset-location">
                              {device.location}
                            </p>
                          )}

                          {device.ip_address && (
                            <p className="asset-address">
                              {device.ip_address}
                            </p>
                          )}
                        </div>

                        <div className="asset-card-footer">
                          <span>
                            {isSelected
                              ? "Selected for scenario"
                              : "Click to select"}
                          </span>

                          <span className="asset-selection-indicator">
                            {isSelected ? "✓" : "+"}
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </>
            )}
          </section>

          {selectedTargets.length > 0 && (
            <section className="selected-impact-preview">
              <div className="selected-impact-heading">
                <div>
                  <p className="scenario-intelligence-eyebrow">
                    Target Impact Preview
                  </p>

                  <h2>Selected Assets</h2>
                </div>

                <span>
                  {selectedTargets.length} targeted
                </span>
              </div>

              <div className="selected-impact-list">
                {selectedDeviceDetails.map((device) => {
                  const currentStatus =
                    device.status ?? "Unknown";

                  const expectedStatus = getExpectedStatus(
                    selectedAttackDetails,
                    currentStatus
                  );

                  const alreadyAffected =
                    isAlreadyAffected(currentStatus);

                  return (
                    <article
                      key={device.id}
                      className={`selected-impact-row ${
                        alreadyAffected
                          ? "already-affected"
                          : ""
                      }`}
                    >
                      <div className="selected-impact-asset">
                        <span
                          className="selected-impact-icon"
                          aria-hidden="true"
                        >
                          {getAssetIcon(
                            device.device_type ?? device.type
                          )}
                        </span>

                        <div>
                          <h3>{device.name}</h3>

                          <p>
                            {device.device_type ??
                              device.type ??
                              "Unknown Asset"}

                            {device.location
                              ? ` — ${device.location}`
                              : ""}
                          </p>
                        </div>
                      </div>

                      <div className="status-transition">
                        <span
                          className={getStatusClass(
                            currentStatus
                          )}
                        >
                          {currentStatus}
                        </span>

                        <span
                          className="status-arrow"
                          aria-hidden="true"
                        >
                          →
                        </span>

                        <span
                          className={getImpactClass(
                            expectedStatus
                          )}
                        >
                          {expectedStatus}
                        </span>
                      </div>

                      {alreadyAffected && (
                        <div className="existing-condition-warning">
                          This asset is already{" "}
                          {currentStatus.toLowerCase()}.
                          Scenario results may represent additional
                          impact.
                        </div>
                      )}
                    </article>
                  );
                })}
              </div>
            </section>
          )}

          <div className="scenario-form-section">
            <label htmlFor="notes">Scenario Notes</label>

            <textarea
              id="notes"
              rows="5"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Describe the purpose of this simulation..."
              disabled={loading}
            />
          </div>

          <button
            className="launch-scenario-button"
            type="submit"
            disabled={
              loading ||
              dataLoading ||
              !selectedAttack ||
              selectedTargets.length === 0
            }
          >
            {loading
              ? "Launching..."
              : `Launch Scenario${
                  selectedTargets.length > 0
                    ? ` (${selectedTargets.length} assets)`
                    : ""
                }`}
          </button>
        </form>

        {error && (
          <div className="scenario-error" role="alert">
            {error}
          </div>
        )}

        <ScenarioResultsDrawer
          result={scenarioResult}
          onClose={() => setScenarioResult(null)}
        />
        <ScenarioResultsDrawer
  result={scenarioResult}
  onClose={() => setScenarioResult(null)}
/>
      </section>
    </main>
  );
}

export default CreateScenario;