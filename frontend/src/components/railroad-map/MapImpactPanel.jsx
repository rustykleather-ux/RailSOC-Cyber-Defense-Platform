const metrics = [
  ["affected_blocks", "Affected blocks"],
  ["stopped_trains", "Stopped trains"],
  ["slowed_trains", "Slowed trains"],
  ["delayed_trains", "Delayed trains"],
  ["cumulative_delay_minutes", "Delay", " min"],
  ["blocked_track_miles", "Blocked track", " mi"],
  ["track_availability_percent", "Track available", "%"],
  ["dispatch_availability_percent", "Dispatch available", "%"],
  ["ptc_restricted_trains", "PTC restrictions"],
];

export default function MapImpactPanel({ impact, onMetric }) {
  return (
    <aside className="dt-impact-panel" aria-label="Operational impact">
      <div className="dt-impact-panel__header">
        <div>
          <span>Live operational consequence</span>
          <h3>Impact Summary</h3>
        </div>
        <span
          className={`dt-impact-panel__state ${
            impact.affected_blocks ||
            impact.stopped_trains ||
            impact.unsafe_switches ||
            impact.affected_crossings
              ? "is-affected"
              : ""
          }`}
        >
          {impact.estimated_recovery || "Operational state available"}
        </span>
      </div>
      <div className="dt-impact-grid">
        {metrics.map(([key, label, suffix = ""]) => (
          <button key={key} type="button" onClick={() => onMetric(key)}>
            <span>{label}</span>
            <strong>
              {impact[key] ?? 0}
              {suffix}
            </strong>
          </button>
        ))}
      </div>
      <p>{impact.summary}</p>
    </aside>
  );
}
