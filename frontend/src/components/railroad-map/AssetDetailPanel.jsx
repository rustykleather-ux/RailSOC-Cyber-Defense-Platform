function display(value) {
  if (value === null || value === undefined || value === "") {
    return "Not reported";
  }
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "None";
  return String(value);
}

function fieldsFor(kind, asset) {
  const common = [
    ["Subdivision", asset.subdivision],
    ["Track", asset.track],
    ["Communications", asset.communications_status],
    ["Security", asset.security_status],
  ];
  const byKind = {
    block: [
      ["Milepost limits", `${asset.start_mp}–${asset.end_mp}`],
      ["Signal", asset.signal_aspect],
      ["Occupied by", asset.occupied_by],
      ["Speed limit", `${asset.speed_limit} MPH`],
      ["Controlling device", asset.controlling_device],
      ["Maintenance", asset.maintenance],
    ],
    signal: [
      ["Milepost", asset.milepost],
      ["Aspect", asset.aspect],
      ["Protected block", asset.block_id],
      ["Controlling device", asset.controlling_device],
    ],
    train: [
      ["Milepost", asset.milepost],
      ["Direction", asset.direction],
      ["Speed", `${asset.speed ?? 0} MPH`],
      ["Target speed", asset.target_speed],
      ["Current block", asset.current_block],
      ["Next block", asset.next_block],
      ["Signal", asset.current_signal],
      ["Status", asset.status],
      ["PTC enabled", asset.ptc_enabled],
      ["Delay", asset.delay_minutes],
      ["Restrictions", asset.operational_restrictions],
    ],
    switch: [
      ["Milepost", asset.milepost],
      ["Position", asset.position],
      ["Commanded position", asset.commanded_position],
      ["Locked", asset.locked],
      ["Controlling device", asset.controlling_device],
    ],
    crossing: [
      ["Milepost", asset.milepost],
      ["Gate state", asset.gate_state],
      ["Warning lights", asset.lights_active],
      ["Warning time", `${asset.warning_time_seconds} sec`],
      ["Controlling device", asset.controlling_device],
    ],
    device: [
      ["Device type", asset.device_type],
      ["Location", asset.location],
      ["Milepost", asset.milepost],
      ["Status", asset.status],
      ["Criticality", asset.criticality],
      ["Risk", `${asset.risk} (${asset.risk_score})`],
      ["Capabilities", asset.capabilities],
    ],
  };
  return [...(byKind[kind] ?? []), ...common];
}

function titleFor(kind, asset) {
  if (kind === "train") return asset.symbol;
  return asset.name;
}

function relatedTimeline(snapshot, kind, asset) {
  return (snapshot.timeline ?? [])
    .filter((event) => {
      if (kind === "device") return event.device_id === asset.id;
      if (kind === "train") return event.train_id === asset.id;
      if (kind === "block") return event.track_block_id === asset.id;
      if (kind === "signal") return event.track_block_id === asset.block_id;
      return event.asset_name === asset.name;
    })
    .slice(0, 5);
}

export default function AssetDetailPanel({
  selected,
  snapshot,
  onClose,
}) {
  if (!selected) return null;
  const { kind, data: asset } = selected;
  const deviceId =
    kind === "device" ? asset.id : asset.controlling_device_id;
  const alerts = snapshot.alerts.filter(
    (alert) => alert.device_id === deviceId && alert.status !== "Closed",
  );
  const incidents = snapshot.incidents.filter(
    (incident) => incident.device_id === deviceId,
  );
  const events = relatedTimeline(snapshot, kind, asset);

  return (
    <>
      <button
        type="button"
        className="dt-detail-backdrop"
        aria-label="Close asset details"
        onClick={onClose}
      />
      <section
        className="dt-detail-panel"
        aria-label={`${titleFor(kind, asset)} details`}
      >
        <header>
          <div>
            <span>{kind.replace("_", " ").toUpperCase()}</span>
            <h3>{titleFor(kind, asset)}</h3>
          </div>
          <button type="button" onClick={onClose} aria-label="Close details">
            ×
          </button>
        </header>

        <section>
          <h4>Live state</h4>
          <dl>
            {fieldsFor(kind, asset).map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{display(value)}</dd>
              </div>
            ))}
          </dl>
        </section>

        {kind === "device" && (
          <section>
            <h4>Controlled and connected assets</h4>
            {asset.relationships?.length ? (
              <ul>
                {asset.relationships.map((relationship) => (
                  <li key={relationship.id}>
                    {relationship.relationship_type.replaceAll("_", " ")} →{" "}
                    {relationship.target_name}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No relationships configured.</p>
            )}
          </section>
        )}

        <section>
          <h4>Active alerts and incidents</h4>
          {alerts.length === 0 && incidents.length === 0 ? (
            <p>No related active cyber records.</p>
          ) : (
            <ul>
              {alerts.map((alert) => (
                <li key={`alert-${alert.id}`}>
                  <strong>{alert.severity}: {alert.alert_type}</strong>
                  <span>{alert.message}</span>
                </li>
              ))}
              {incidents.slice(0, 3).map((incident) => (
                <li key={`incident-${incident.id}`}>
                  <strong>Incident #{incident.id}: {incident.status}</strong>
                  <span>{incident.message}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h4>Recent timeline events</h4>
          {events.length ? (
            <ul>
              {events.map((event) => (
                <li key={event.id}>
                  <strong>{event.title}</strong>
                  <span>{event.message}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p>No related timeline events.</p>
          )}
        </section>
      </section>
    </>
  );
}
