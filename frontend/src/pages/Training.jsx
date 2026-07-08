function Training({ simulateAttack, resetDemo }) {
  const scenarios = [
    {
      id: "firmware",
      title: "Unauthorized PLC Firmware Modification",
      asset: "Grade Crossing Controller MP 82.4",
      severity: "Critical",
      mitre: "T0859 - Modify Controller Tasking",
      difficulty: "Advanced",
      description:
        "Simulates unauthorized firmware modification of a critical signal controller.",
    },
    {
      id: "recon",
      title: "Network Reconnaissance",
      asset: "Dispatch Network",
      severity: "Medium",
      mitre: "T0842 - Network Service Scanning",
      difficulty: "Beginner",
      description:
        "Simulates discovery activity against railroad operational assets.",
    },
    {
      id: "dos",
      title: "Rail OT Denial of Service",
      asset: "Dispatch SCADA Server",
      severity: "Critical",
      mitre: "T0814 - Denial of Service",
      difficulty: "Advanced",
      description:
        "Simulates degradation of communications to dispatch systems without generating real network traffic.",
    },
    {
      id: "auth",
      title: "Engineering Workstation Credential Abuse",
      asset: "Engineering Workstation",
      severity: "High",
      mitre: "T0812 - Valid Accounts",
      difficulty: "Intermediate",
      description:
        "Simulates repeated authentication attempts leading to unauthorized engineering access.",
    },
    {
      id: "ptc",
      title: "PTC Communications Failure",
      asset: "PTC Radio Gateway",
      severity: "High",
      mitre: "T0881 - Service Stop",
      difficulty: "Intermediate",
      description:
        "Simulates loss of communications between Positive Train Control components.",
    },
    {
      id: "malware",
      title: "Malware on Engineering Station",
      asset: "Engineering Workstation",
      severity: "Critical",
      mitre: "T0809 - Data Destruction",
      difficulty: "Advanced",
      description:
        "Simulates malware execution impacting engineering operations.",
    },
  ];

  return (
    <section className="purple-team-page">
      <div className="purple-header">
        <div>
          <h2>Purple Team Attack Library</h2>
          <p>
            Launch realistic railroad OT attack simulations for analyst training
            and incident response exercises.
          </p>
        </div>

        <button className="reset-button" onClick={resetDemo}>
          Restore Operational Baseline
        </button>
      </div>

      <div className="scenario-grid">
        {scenarios.map((scenario) => (
          <div className="scenario-card" key={scenario.id}>
            <span
              className={`badge ${scenario.severity.toLowerCase()}`}
            >
              {scenario.severity}
            </span>

            <h3>{scenario.title}</h3>

            <p>{scenario.description}</p>

            <table className="scenario-table">
              <tbody>
                <tr>
                  <td>Target</td>
                  <td>{scenario.asset}</td>
                </tr>

                <tr>
                  <td>MITRE</td>
                  <td>{scenario.mitre}</td>
                </tr>

                <tr>
                  <td>Difficulty</td>
                  <td>{scenario.difficulty}</td>
                </tr>
              </tbody>
            </table>

            <button
              className="launch-button"
              onClick={() => simulateAttack(scenario.id)}
            >
              Launch Scenario
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}

export default Training;