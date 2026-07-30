import { memo } from "react";
import {
  assetState,
  blockState,
  controlledAssetKeys,
  dispatchCommandState,
  matchesFilters,
  trainState,
} from "./mapLayout";

function activate(event, callback) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    callback();
  }
}

function selectableProps(label, onSelect) {
  return {
    role: "button",
    tabIndex: 0,
    "aria-label": label,
    onClick: onSelect,
    onKeyDown: (event) => activate(event, onSelect),
  };
}

function stateLabel(state) {
  return {
    security: "SEC",
    communications: "COMMS",
    maintenance: "MNT",
    stop: "STOP",
    approach: "APP",
    occupied: "OCC",
    normal: "OK",
  }[state] ?? state.toUpperCase();
}

function Signal({
  signal,
  x,
  y,
  onSelect,
  onHover = () => {},
  changed,
  highlighted,
}) {
  const aspect = String(signal.aspect || "unknown").toLowerCase();
  const compromised =
    String(signal.security_status).toLowerCase() === "compromised";
  return (
    <g
      className={`dt-signal dt-signal--${aspect} ${
        changed ? "is-changed" : ""
      } ${highlighted ? "is-highlighted" : ""} ${
        compromised ? "is-compromised" : ""
      }`}
      transform={`translate(${x} ${y - 48})`}
      onMouseEnter={() => onHover("signal", signal)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover("signal", signal)}
      onBlur={() => onHover(null)}
      {...selectableProps(
        `${signal.name}, ${signal.aspect || "Unknown"}`,
        onSelect,
      )}
    >
      <title>
        {signal.name} · {signal.aspect} · {signal.controlling_device} · Security{" "}
        {signal.security_status} · Communications{" "}
        {signal.communications_status}
      </title>
      <line x1="0" y1="10" x2="0" y2="42" />
      <rect x="-7" y="-12" width="14" height="25" rx="5" />
      <circle cx="0" cy="0" r="5" />
      <text x="11" y="3">{signal.aspect || "Unknown"}</text>
    </g>
  );
}

function Train({
  train,
  x,
  y,
  onSelect,
  onHover,
  changed,
  highlighted,
}) {
  const state = trainState(train);
  const westbound = String(train.direction).toLowerCase() === "westbound";
  const statusLabel = {
    stopped: "■ STOPPED AT SIGNAL",
    ptc: "▲ PTC RESTRICTED",
    delayed: "◆ DELAYED",
    emergency: "■ EMERGENCY STOP",
    communications: "◆ COMMS LOST",
    slowing: "▲ SLOWING",
    moving: "● Moving",
  }[state];
  return (
    <g
      className={`dt-train dt-train--${state} ${
        changed ? "is-changed" : ""
      } ${highlighted ? "is-highlighted" : ""}`}
      style={{ transform: `translate(${x}px, ${y - 105}px)` }}
      onMouseEnter={() => onHover("train", train)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover("train", train)}
      onBlur={() => onHover(null)}
      {...selectableProps(
        `${train.symbol}, ${train.status}, ${train.speed} miles per hour`,
        onSelect,
      )}
    >
      <title>
        {train.symbol} · {train.speed ?? 0} MPH · {train.status} · Current{" "}
        {train.current_block || "unknown"} · Next {train.next_block || "unknown"}
      </title>
      <rect
        className="dt-train__badge"
        x="-70"
        y="-73"
        width="140"
        height="45"
        rx="9"
      />
      <text className="dt-train__symbol" x="0" y="-56" textAnchor="middle">
        {westbound ? "←" : "→"} {train.symbol} · {train.speed ?? 0} MPH
      </text>
      <text className="dt-train__status" x="0" y="-39" textAnchor="middle">
        {statusLabel}
      </text>

      <g
        className={`dt-locomotive ${
          westbound ? "dt-locomotive--westbound" : ""
        }`}
      >
        <path
          className="dt-locomotive__body"
          d="M-67 3H-34L-25-18H10L22-7H53L66 4V28H-67Z"
        />
        <path
          className="dt-locomotive__roof"
          d="M-31-18H11L20-8H-35Z"
        />
        <path
          className="dt-locomotive__nose"
          d="M53-7L68 4V17H50V-7Z"
        />
        <path
          className="dt-locomotive__window"
          d="M-20-13H6L14-6H-23Z"
        />
        <path
          className="dt-locomotive__stripe"
          d="M-65 13H64V20H-65Z"
        />
        <g className="dt-locomotive__vents">
          <line x1="24" y1="-2" x2="24" y2="10" />
          <line x1="31" y1="-2" x2="31" y2="10" />
          <line x1="38" y1="-2" x2="38" y2="10" />
          <line x1="45" y1="-2" x2="45" y2="10" />
        </g>
        <rect
          className="dt-locomotive__number"
          x="-18"
          y="1"
          width="25"
          height="10"
          rx="2"
        />
        <text x="-5.5" y="9" textAnchor="middle">
          {String(train.symbol || "").replace(/\D/g, "").slice(-4) || "218"}
        </text>
        <circle className="dt-locomotive__headlight" cx="61" cy="3" r="3.5" />
        <path className="dt-locomotive__pilot" d="M56 28H70L64 34H51Z" />
        <line className="dt-locomotive__coupler" x1="68" y1="25" x2="78" y2="25" />
        <g className="dt-locomotive__truck">
          <path d="M-54 27H-19L-15 34H-58Z" />
          <path d="M18 27H52L57 34H14Z" />
          <circle cx="-48" cy="35" r="7" />
          <circle cx="-27" cy="35" r="7" />
          <circle cx="24" cy="35" r="7" />
          <circle cx="47" cy="35" r="7" />
        </g>
        <line className="dt-locomotive__rail-shadow" x1="-76" y1="43" x2="78" y2="43" />
      </g>
    </g>
  );
}

function TrackSwitchMarker({
  item,
  x,
  y,
  onSelect,
  onHover,
  changed,
  highlighted,
}) {
  const state = assetState(item);
  const reverse = String(item.position).toLowerCase() !== "normal";
  return (
    <g
      className={`dt-switch dt-asset--${state} ${
        changed ? "is-changed" : ""
      } ${highlighted ? "is-highlighted" : ""}`}
      transform={`translate(${x} ${y})`}
      onMouseEnter={() => onHover("switch", item)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover("switch", item)}
      onBlur={() => onHover(null)}
      {...selectableProps(
        `${item.name}, ${item.position}, ${
          item.locked ? "locked" : "unlocked"
        }`,
        onSelect,
      )}
    >
      <title>
        {item.name} · Position {item.position} · Commanded{" "}
        {item.commanded_position} · {item.locked ? "Locked" : "Unlocked"}
      </title>
      <path d="M-24 0h48" />
      <path d={reverse ? "M-10 0L25 -28" : "M-10 0L25 28"} />
      <circle cx="-10" cy="0" r="5" />
      <rect x="-18" y="18" width="36" height="17" rx="4" />
      <text x="0" y="30" textAnchor="middle">
        {item.locked ? "LOCKED" : item.position}
      </text>
    </g>
  );
}

function Crossing({
  item,
  x,
  y,
  onSelect,
  onHover,
  changed,
  highlighted,
}) {
  const state = assetState(item);
  return (
    <g
      className={`dt-crossing dt-asset--${state} ${
        changed ? "is-changed" : ""
      } ${highlighted ? "is-highlighted" : ""}`}
      transform={`translate(${x} ${y + 72})`}
      onMouseEnter={() => onHover("crossing", item)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover("crossing", item)}
      onBlur={() => onHover(null)}
      {...selectableProps(
        `${item.name}, gate ${item.gate_state}, lights ${
          item.lights_active ? "active" : "inactive"
        }`,
        onSelect,
      )}
    >
      <title>
        {item.name} · Gate {item.gate_state} · Warning lights{" "}
        {item.lights_active ? "active" : "inactive"} · Security{" "}
        {item.security_status}
      </title>
      <path d="M-13 -13L13 13M13 -13L-13 13" />
      <line x1="0" y1="13" x2="0" y2="38" />
      <circle cx="-17" cy="26" r="4" />
      <circle cx="17" cy="26" r="4" />
      <text x="0" y="53" textAnchor="middle">
        {item.gate_state} · {item.lights_active ? "LIGHTS" : "NO LIGHTS"}
      </text>
    </g>
  );
}

function Device({
  item,
  x,
  y,
  onSelect,
  onHover,
  changed,
  highlighted,
}) {
  const state = assetState(item);
  return (
    <g
      className={`dt-device dt-asset--${state} ${
        changed ? "is-changed" : ""
      } ${highlighted ? "is-highlighted" : ""}`}
      transform={`translate(${x} ${y + 105})`}
      onMouseEnter={() => onHover("device", item)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover("device", item)}
      onBlur={() => onHover(null)}
      {...selectableProps(
        `${item.name}, ${item.device_type}, ${item.status}`,
        onSelect,
      )}
    >
      <title>
        {item.name} · {item.device_type} · {item.status} · Risk {item.risk} ·
        Security {item.security_status} · Communications{" "}
        {item.communications_status}
      </title>
      <line x1="0" y1="-48" x2="0" y2="-20" />
      <rect x="-44" y="-20" width="88" height="42" rx="7" />
      <text x="0" y="-3" textAnchor="middle">
        {item.name.length > 18 ? `${item.name.slice(0, 17)}…` : item.name}
      </text>
      <text x="0" y="13" textAnchor="middle">
        {item.status} · {item.risk}
      </text>
    </g>
  );
}

function blockKey(id) {
  return `TRACK_BLOCK:${id}`;
}

function DigitalTwinSvg({
  snapshot,
  dimensions,
  filters,
  layers,
  selected,
  onSelect,
  onHover = () => {},
  changedKeys,
  highlightedKeys,
}) {
  const selectedControlled = new Set(
    selected?.kind === "device" ? controlledAssetKeys(selected.data) : [],
  );
  const isHighlighted = (key) =>
    selectedControlled.has(key) || highlightedKeys.has(key);
  const typeVisible = (type) =>
    filters.assetType === "all" || filters.assetType === type;
  const commandClass = (targetType, targetId) => {
    const state = dispatchCommandState(
      snapshot.dispatch_commands,
      targetType,
      targetId,
    );
    return state ? `has-command-${state}` : "";
  };
  const routeClass = (blockId) =>
    (snapshot.dispatch_routes ?? []).some(
      (route) =>
        ["Established", "Occupied"].includes(route.status) &&
        route.requested_path?.some(
          (routeBlockId) => String(routeBlockId) === String(blockId),
        ),
    )
      ? "is-route-reserved"
      : "";
  const restrictionClass = (targetType, targetId) =>
    (snapshot.operational_restrictions ?? []).some(
      (restriction) =>
        restriction.active &&
        restriction.target_type === targetType &&
        String(restriction.target_id) === String(targetId),
    )
      ? "has-operational-restriction"
      : "";

  const corridorByName = Object.fromEntries(
    dimensions.corridors.map((item) => [item.name, item]),
  );
  const corridorFor = (asset) =>
    corridorByName[asset.subdivision] ?? dimensions.corridors[0];
  const yFor = (asset, corridor) =>
    corridor?.trackY?.[asset.track || "Main"] ??
    Object.values(corridor?.trackY ?? {})[0];

  const positionForRelationship = (key) => {
    const [type, rawId] = key.split(":");
    const id = Number(rawId);
    const collections = {
      TRACK_BLOCK: snapshot.blocks,
      TRACK_SWITCH: snapshot.switches,
      GRADE_CROSSING: snapshot.crossings,
    };
    const asset = collections[type]?.find((item) => item.id === id);
    if (!asset) return null;
    const corridor = corridorFor(asset);
    const milepost =
      asset.milepost ?? (asset.start_mp + asset.end_mp) / 2;
    return {
      x: corridor.xFor(milepost),
      y: yFor(asset, corridor),
    };
  };

  const selectedDevicePosition =
    selected?.kind === "device"
      ? (() => {
          const corridor = corridorFor(selected.data);
          if (!corridor || selected.data.milepost == null) return null;
          return {
            x: corridor.xFor(selected.data.milepost),
            y: yFor(selected.data, corridor) + 105,
          };
        })()
      : null;

  return (
    <svg
      className="digital-twin-svg"
      width={dimensions.width}
      height={dimensions.height}
      viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
      role="img"
      aria-labelledby="digital-twin-map-title digital-twin-map-description"
    >
      <title id="digital-twin-map-title">
        TrackSentinel railroad digital twin map
      </title>
      <desc id="digital-twin-map-description">
        Schematic railroad subdivisions positioned by milepost with live blocks,
        signals, trains, switches, crossings, and OT devices.
      </desc>
      <defs>
        <pattern
          id="security-pattern"
          width="10"
          height="10"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <rect width="4" height="10" className="pattern-security" />
        </pattern>
        <pattern
          id="maintenance-pattern"
          width="12"
          height="12"
          patternUnits="userSpaceOnUse"
        >
          <path d="M0 12L12 0" className="pattern-maintenance" />
        </pattern>
        <pattern
          id="occupancy-pattern"
          width="10"
          height="10"
          patternUnits="userSpaceOnUse"
        >
          <circle cx="5" cy="5" r="2.2" className="pattern-occupancy" />
        </pattern>
        <filter id="train-shadow" x="-30%" y="-30%" width="160%" height="180%">
          <feDropShadow dx="0" dy="5" stdDeviation="5" floodOpacity="0.55" />
        </filter>
        <filter id="signal-glow" x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur stdDeviation="3.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {dimensions.corridors.map((corridor) => {
        const visibleBlocks = snapshot.blocks.filter(
          (block) =>
            block.subdivision === corridor.name &&
            matchesFilters({ ...block, type: "block" }, filters),
        );
        const scaleStep = Math.max(
          1,
          Math.ceil(
            (corridor.maximum_milepost - corridor.minimum_milepost) / 10,
          ),
        );
        const scale = [];
        for (
          let mp = Math.ceil(corridor.minimum_milepost);
          mp <= corridor.maximum_milepost;
          mp += scaleStep
        ) {
          scale.push(mp);
        }
        return (
          <g key={corridor.name} className="dt-corridor">
            <text
              x="20"
              y={corridor.top + 25}
              className="dt-corridor__title"
            >
              {corridor.name}
            </text>
            <text
              x="20"
              y={corridor.top + 45}
              className="dt-corridor__range"
            >
              MP {corridor.minimum_milepost.toFixed(1)}–MP{" "}
              {corridor.maximum_milepost.toFixed(1)}
            </text>

            {scale.map((milepost) => {
              const x = corridor.xFor(milepost);
              return (
                <g key={milepost} className="dt-milepost">
                  <line
                    x1={x}
                    y1={corridor.top + 52}
                    x2={x}
                    y2={corridor.top + corridor.height - 40}
                  />
                  {layers.mileposts && (
                    <text x={x} y={corridor.top + 62} textAnchor="middle">
                      MP {milepost}
                    </text>
                  )}
                </g>
              );
            })}

            {corridor.tracks.map((track) => {
              const y = corridor.trackY[track];
              return (
                <g key={track} className="dt-track">
                  <text x="20" y={y + 5}>
                    {track}
                  </text>
                  <line x1="70" y1={y - 5} x2={corridor.width - 70} y2={y - 5} />
                  <line x1="70" y1={y + 5} x2={corridor.width - 70} y2={y + 5} />
                </g>
              );
            })}

            {layers.blocks &&
              typeVisible("block") &&
              visibleBlocks.map((block) => {
                const y = yFor(block, corridor);
                const x1 = corridor.xFor(block.start_mp);
                const x2 = corridor.xFor(block.end_mp);
                const state = blockState(block);
                const key = blockKey(block.id);
                return (
                  <g
                    key={key}
                    className={`dt-block dt-block--${state} ${
                      changedKeys.has(key) ? "is-changed" : ""
                    } ${isHighlighted(key) ? "is-highlighted" : ""} ${commandClass(
                      "TRACK_BLOCK",
                      block.id,
                    )} ${routeClass(block.id)} ${restrictionClass(
                      "TRACK_BLOCK",
                      block.id,
                    )}`}
                    {...selectableProps(
                      `${block.name}, milepost ${block.start_mp} to ${
                        block.end_mp
                      }, ${stateLabel(state)}, signal ${block.signal_aspect}`,
                      () => onSelect("block", block),
                    )}
                    onMouseEnter={() => onHover("block", block)}
                    onMouseLeave={() => onHover(null)}
                    onFocus={() => onHover("block", block)}
                    onBlur={() => onHover(null)}
                  >
                    <title>
                      {block.name} · MP {block.start_mp}–{block.end_mp} · Signal{" "}
                      {block.signal_aspect} · {block.occupied_by || "Unoccupied"} ·
                      Controller {block.controlling_device || "None"} · Security{" "}
                      {block.security_status} · Communications{" "}
                      {block.communications_status}
                    </title>
                    <rect
                      x={x1}
                      y={y - 24}
                      width={Math.max(x2 - x1, 5)}
                      height="48"
                      rx="4"
                    />
                    {state === "security" && (
                      <rect
                        x={x1}
                        y={y - 24}
                        width={Math.max(x2 - x1, 5)}
                        height="48"
                        rx="4"
                        fill="url(#security-pattern)"
                      />
                    )}
                    {state === "maintenance" && (
                      <rect
                        x={x1}
                        y={y - 24}
                        width={Math.max(x2 - x1, 5)}
                        height="48"
                        rx="4"
                        fill="url(#maintenance-pattern)"
                      />
                    )}
                    <text x={(x1 + x2) / 2} y={y - 7} textAnchor="middle">
                      {block.name}
                    </text>
                    <text x={(x1 + x2) / 2} y={y + 12} textAnchor="middle">
                      {stateLabel(state)} · {block.signal_aspect}
                    </text>
                    <line x1={x1} y1={y - 32} x2={x1} y2={y + 32} />
                  </g>
                );
              })}
          </g>
        );
      })}

      {layers.relationships &&
        selectedDevicePosition &&
        [...selectedControlled].map((key) => {
          const target = positionForRelationship(key);
          return target ? (
            <line
              key={`relationship-${key}`}
              className="dt-relationship"
              x1={selectedDevicePosition.x}
              y1={selectedDevicePosition.y}
              x2={target.x}
              y2={target.y}
            />
          ) : null;
        })}

      {layers.signals &&
        typeVisible("signal") &&
        snapshot.signals
          .filter((item) => matchesFilters(item, filters))
          .map((signal) => {
            const corridor = corridorFor(signal);
            if (!corridor) return null;
            return (
              <Signal
                key={signal.id}
                signal={signal}
                x={corridor.xFor(signal.milepost)}
                y={yFor(signal, corridor)}
                onSelect={() => onSelect("signal", signal)}
                onHover={onHover}
                changed={changedKeys.has(`SIGNAL:${signal.id}`)}
                highlighted={
                  isHighlighted(blockKey(signal.block_id)) ||
                  Boolean(commandClass("TRACK_BLOCK", signal.block_id))
                }
              />
            );
          })}

      {layers.switches &&
        typeVisible("switch") &&
        snapshot.switches
          .filter((item) => matchesFilters(item, filters))
          .map((item) => {
            const corridor = corridorFor(item);
            if (!corridor) return null;
            const key = `TRACK_SWITCH:${item.id}`;
            return (
              <TrackSwitchMarker
                key={key}
                item={item}
                x={corridor.xFor(item.milepost)}
                y={yFor(item, corridor)}
                onSelect={() => onSelect("switch", item)}
                onHover={onHover}
                changed={changedKeys.has(key)}
                highlighted={
                  isHighlighted(key) ||
                  Boolean(commandClass("TRACK_SWITCH", item.id))
                }
              />
            );
          })}

      {layers.crossings &&
        typeVisible("crossing") &&
        snapshot.crossings
          .filter((item) => matchesFilters(item, filters))
          .map((item) => {
            const corridor = corridorFor(item);
            if (!corridor) return null;
            const key = `GRADE_CROSSING:${item.id}`;
            return (
              <Crossing
                key={key}
                item={item}
                x={corridor.xFor(item.milepost)}
                y={yFor(item, corridor)}
                onSelect={() => onSelect("crossing", item)}
                onHover={onHover}
                changed={changedKeys.has(key)}
                highlighted={
                  isHighlighted(key) ||
                  Boolean(commandClass("GRADE_CROSSING", item.id))
                }
              />
            );
          })}

      {layers.trains &&
        typeVisible("train") &&
        snapshot.trains
          .filter((item) => matchesFilters(item, filters))
          .map((train) => {
            const corridor = corridorFor(train);
            if (!corridor) return null;
            const key = `TRAIN:${train.id}`;
            return (
              <Train
                key={key}
                train={train}
                x={corridor.xFor(train.milepost)}
                y={yFor(train, corridor)}
                onSelect={() => onSelect("train", train)}
                onHover={onHover}
                changed={changedKeys.has(key)}
                highlighted={
                  highlightedKeys.has(key) ||
                  Boolean(commandClass("TRAIN", train.id))
                }
              />
            );
          })}

      {layers.devices &&
        typeVisible("device") &&
        snapshot.devices
          .filter(
            (item) =>
              item.milepost != null &&
              matchesFilters(item, filters),
          )
          .map((item) => {
            const corridor = corridorFor(item);
            if (!corridor) return null;
            const key = `OT_DEVICE:${item.id}`;
            return (
              <Device
                key={key}
                item={item}
                x={corridor.xFor(item.milepost)}
                y={yFor(item, corridor)}
                onSelect={() => onSelect("device", item)}
                onHover={onHover}
                changed={changedKeys.has(key)}
                highlighted={
                  isHighlighted(key) ||
                  Boolean(commandClass("OT_DEVICE", item.id))
                }
              />
            );
          })}
    </svg>
  );
}

export default memo(DigitalTwinSvg);
