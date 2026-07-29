const layerLabels = {
  trains: "Trains",
  signals: "Signals",
  switches: "Switches",
  crossings: "Crossings",
  devices: "OT devices",
  relationships: "Relationship highlights",
  mileposts: "Milepost labels",
  impact: "Operational impact",
};

export default function MapControls({
  snapshot,
  filters,
  onFilters,
  layers,
  onLayers,
  zoom,
  onZoom,
  onReset,
}) {
  const subdivisions = snapshot.subdivisions.map((item) => item.name);
  const tracks = [
    ...new Set(snapshot.subdivisions.flatMap((item) => item.tracks)),
  ];
  return (
    <div className="dt-controls" aria-label="Map controls">
      <div className="dt-controls__filters">
        <label>
          Subdivision
          <select
            value={filters.subdivision}
            onChange={(event) =>
              onFilters({ ...filters, subdivision: event.target.value })
            }
          >
            <option value="all">All subdivisions</option>
            {subdivisions.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label>
          Track
          <select
            value={filters.track}
            onChange={(event) =>
              onFilters({ ...filters, track: event.target.value })
            }
          >
            <option value="all">All tracks</option>
            {tracks.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label>
          Asset type
          <select
            value={filters.assetType}
            onChange={(event) =>
              onFilters({ ...filters, assetType: event.target.value })
            }
          >
            <option value="all">All assets</option>
            <option value="block">Track blocks</option>
            <option value="signal">Signals</option>
            <option value="train">Trains</option>
            <option value="switch">Switches</option>
            <option value="crossing">Crossings</option>
            <option value="device">OT devices</option>
          </select>
        </label>
        <label>
          Operational state
          <select
            value={filters.operational}
            onChange={(event) =>
              onFilters({ ...filters, operational: event.target.value })
            }
          >
            <option value="all">All states</option>
            <option value="security">Security compromised</option>
            <option value="communications">Communications issue</option>
            <option value="maintenance">Maintenance</option>
            <option value="stop">Stopped / unavailable</option>
            <option value="approach">Restricted / slowing</option>
            <option value="occupied">Occupied</option>
            <option value="normal">Normal</option>
          </select>
        </label>
        <label>
          Security
          <select
            value={filters.security}
            onChange={(event) =>
              onFilters({ ...filters, security: event.target.value })
            }
          >
            <option value="all">Any security state</option>
            <option value="healthy">Healthy</option>
            <option value="compromised">Compromised</option>
          </select>
        </label>
        <label>
          Communications
          <select
            value={filters.communications}
            onChange={(event) =>
              onFilters({
                ...filters,
                communications: event.target.value,
              })
            }
          >
            <option value="all">Any communications state</option>
            <option value="online">Online</option>
            <option value="degraded">Degraded</option>
            <option value="offline">Offline</option>
          </select>
        </label>
      </div>

      <div className="dt-controls__layers">
        {Object.entries(layerLabels).map(([key, label]) => (
          <label key={key}>
            <input
              type="checkbox"
              checked={layers[key]}
              onChange={(event) =>
                onLayers({ ...layers, [key]: event.target.checked })
              }
            />
            {label}
          </label>
        ))}
      </div>

      <div className="dt-controls__view">
        <button type="button" onClick={() => onZoom(Math.max(0.65, zoom - 0.2))}>
          − Zoom out
        </button>
        <span aria-live="polite">{Math.round(zoom * 100)}%</span>
        <button type="button" onClick={() => onZoom(Math.min(2.5, zoom + 0.2))}>
          + Zoom in
        </button>
        <button type="button" onClick={() => onZoom(1)}>
          Fit subdivision
        </button>
        <button type="button" onClick={onReset}>
          Reset view
        </button>
      </div>
    </div>
  );
}
