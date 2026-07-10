function Metric({ label, value }) {
  if (value === undefined || value === null) return null;

  return (
    <div className="metric-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

import {
  TrafficCone,
  Construction,
  MonitorCog,
  Laptop,
  Database,
  ShieldCheck,
  RadioTower,
  Wifi,
  Zap,
  PlugZap,
  Flame,
  Thermometer,
  DoorOpen,
  Landmark,
  GitBranch,
  Box,
} from "lucide-react";

function getIcon(type) {
  const iconProps = {
    size: 24,
    strokeWidth: 1.8,
    "aria-hidden": true,
  };

  switch (type) {
    case "Signal Controller":
      return <TrafficCone {...iconProps} />;

    case "Grade Crossing Controller":
      return <Construction {...iconProps} />;

    case "Dispatch SCADA":
      return <MonitorCog {...iconProps} />;

    case "Engineering Workstation":
      return <Laptop {...iconProps} />;

    case "Historian":
      return <Database {...iconProps} />;

    case "Jump Server":
      return <ShieldCheck {...iconProps} />;

    case "PTC Communications Gateway":
      return <RadioTower {...iconProps} />;

    case "Communications":
      return <Wifi {...iconProps} />;

    case "Power":
      return <Zap {...iconProps} />;

    case "PLC":
      return <PlugZap {...iconProps} />;

    case "Safety":
      return <Flame {...iconProps} />;

    case "Environmental":
      return <Thermometer {...iconProps} />;

    case "Physical Security":
      return <DoorOpen {...iconProps} />;

    case "Infrastructure":
      return <Landmark {...iconProps} />;

    case "Switch Controller":
      return <GitBranch {...iconProps} />;

    default:
      return <Box {...iconProps} />;
  }
}


function DeviceMetrics({ item }) {
  switch (item.type) {
    case "Signal Controller":
    case "Grade Crossing Controller":
    case "Switch Controller":
      return (
        <>
          <Metric label="Temperature" value={`${item.temperature}°F`} />
          <Metric label="Controller CPU" value={`${item.cpu_usage}%`} />
          <Metric label="Memory" value={`${item.memory_usage}%`} />
        </>
      );

    case "Dispatch SCADA":
    case "Historian":
    case "Jump Server":
      return (
        <>
          <Metric label="CPU Usage" value={`${item.cpu_usage}%`} />
          <Metric label="Memory" value={`${item.memory_usage}%`} />
          <Metric label="Active Sessions" value={item.active_sessions} />
        </>
      );

    case "Engineering Workstation":
      return (
        <>
          <Metric label="CPU Usage" value={`${item.cpu_usage}%`} />
          <Metric label="Memory" value={`${item.memory_usage}%`} />
          <Metric label="Failed Logins" value={item.failed_logins} />
        </>
      );

    case "PTC Communications Gateway":
      return (
        <>
          <Metric label="Power Output" value={`${item.power_output_kw} kW`} />
          <Metric label="Voltage" value={`${item.voltage} V`} />
        </>
      );

    case "Communications":
      return (
        <>
          <Metric label="Signal Quality" value={`${item.signal_quality}%`} />
          <Metric label="Packet Loss" value={`${item.packet_loss}%`} />
          <Metric
            label="Bandwidth"
            value={`${item.bandwidth_utilization}%`}
          />
        </>
      );

    case "Power":
    case "PLC":
      return (
        <>
          <Metric label="Voltage" value={`${item.voltage} V`} />
          <Metric label="Load" value={`${item.load_percent}%`} />
          <Metric label="Battery" value={`${item.battery_percent}%`} />
          <Metric label="Runtime" value={`${item.runtime_minutes} min`} />
        </>
      );

    case "Safety":
      return (
        <>
          <Metric label="Smoke Level" value={item.smoke_level} />
          <Metric label="Heat Alarm" value={item.heat_alarm} />
          <Metric label="Panel Battery" value={`${item.panel_battery}%`} />
        </>
      );

    case "Environmental":
      return (
        <>
          <Metric label="Temperature" value={`${item.temperature}°F`} />
          <Metric label="Humidity" value={`${item.humidity}%`} />
          <Metric label="Gas Level" value={`${item.gas_ppm} ppm`} />
          <Metric label="Water Detected" value={item.water_detected} />
        </>
      );

    case "Physical Security":
      return (
        <>
          <Metric label="Door State" value={item.door_state} />
          <Metric label="Tamper Alarm" value={item.tamper_alarm} />
        </>
      );

    case "Infrastructure":
      return (
        <>
          <Metric label="Vibration" value={`${item.vibration} g`} />
          <Metric label="Temperature" value={`${item.temperature}°F`} />
          <Metric
            label="Bearing Temp"
            value={`${item.bearing_temperature}°F`}
          />
        </>
      );

    default:
      return null;
  }
}

function TelemetryCard({ item }) {
  const conditionClass = item.condition === "Normal" ? "low" : "high";

  return (
    <div className={`plant-card ${(item.status || "unknown").toLowerCase()}`}>
      <h3 className="device-title">
        <span className="device-icon">{getIcon(item.type)}</span>
        {item.device || "Unknown Rail Asset"}
      </h3>

      <p className="plant-type">{item.type || "Rail Asset"}</p>

      <div className="metric-block">
        <Metric label="Status" value={item.status || "Unknown"} />

        <div className="metric-row">
          <span>Operational State</span>
          <strong>
            <span className={`badge ${conditionClass}`}>
              {item.condition || "Unknown"}
            </span>
          </strong>
        </div>

        <DeviceMetrics item={item} />

        <Metric
          label="Network Latency"
          value={`${item.network_latency ?? "Unknown"} ms`}
        />
      </div>

      <small>
        Updated{" "}
        {item.timestamp
          ? new Date(item.timestamp).toLocaleTimeString()
          : "Unknown"}
      </small>
    </div>
  );
}

function LivePlantStatus({ plantStatus }) {
  const categories = {
    "Operations Systems": ["Dispatch SCADA", "Historian", "Jump Server"],
    "Signal & Crossing Systems": [
      "Signal Controller",
      "Grade Crossing Controller",
      "Switch Controller",
    ],
    Communications: ["PTC Communications Gateway", "Communications"],
    "Power Systems": ["Power", "PLC"],
    "Safety & Environmental": [
      "Safety",
      "Environmental",
      "Physical Security",
    ],
    Infrastructure: ["Infrastructure"],
    "Engineering Access": ["Engineering Workstation"],
  };

  const getItemsForCategory = (types) => {
    return (plantStatus || []).filter((item) => types.includes(item.type));
  };

  return (
    <>
      <h2>Live Railroad Asset Status</h2>

      <p className="simulation-subtitle">
        Real-time operational telemetry grouped by railroad OT asset category.
      </p>

      <div className="telemetry-category-list">
        {Object.entries(categories).map(([categoryName, types]) => {
          const items = getItemsForCategory(types);

          if (items.length === 0) return null;

          return (
            <section className="telemetry-category" key={categoryName}>
              <div className="telemetry-category-header">
                <h3>{categoryName}</h3>
                <span>{items.length} assets</span>
              </div>

              <div className="plant-grid">
                {items.map((item, index) => (
                  <TelemetryCard
                    key={`${item.device}-${index}`}
                    item={item}
                  />
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </>
  );
}
export default LivePlantStatus;