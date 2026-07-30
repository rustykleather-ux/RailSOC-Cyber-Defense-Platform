export const MAP_PADDING = 70;
export const TRACK_GAP = 170;
// Reserve enough vertical clearance for the enlarged train badge above track 1.
export const SUBDIVISION_HEADER = 190;
export const SUBDIVISION_GAP = 50;

export function normalize(value) {
  return String(value ?? "").trim().toLowerCase();
}

export function blockState(block) {
  const security = normalize(block.security_status);
  const communications = normalize(block.communications_status);
  const signal = normalize(block.signal_aspect);
  if (security && !["healthy", "normal", "low"].includes(security)) {
    return "security";
  }
  if (
    communications &&
    !["online", "normal", "healthy"].includes(communications)
  ) {
    return "communications";
  }
  if (block.maintenance) return "maintenance";
  if (["stop", "dark", "unknown"].includes(signal)) return "stop";
  if (["approach", "restricting", "restricted"].includes(signal)) {
    return "approach";
  }
  if (block.occupied) return "occupied";
  return "normal";
}

export function assetState(asset) {
  const security = normalize(asset.security_status);
  const communications = normalize(asset.communications_status);
  const status = normalize(asset.status);
  if (
    security === "compromised" ||
    ["compromised", "critical", "emergency stop"].includes(status)
  ) {
    return "security";
  }
  if (
    communications &&
    !["online", "normal", "healthy"].includes(communications)
  ) {
    return "communications";
  }
  if (
    status.includes("stopped") ||
    status.includes("offline") ||
    asset.locked ||
    normalize(asset.gate_state) === "unavailable"
  ) {
    return "stop";
  }
  if (
    status.includes("restricted") ||
    status.includes("slowing") ||
    status.includes("delayed")
  ) {
    return "approach";
  }
  return "normal";
}

export function trainState(train) {
  const status = normalize(train.status);
  if (status.includes("emergency")) return "emergency";
  if (status.includes("communications lost")) return "communications";
  if (status.includes("restricted - ptc")) return "ptc";
  if (status.includes("stopped")) return "stopped";
  if (status.includes("delayed")) return "delayed";
  if (status.includes("slowing") || Number(train.speed) < 25) return "slowing";
  return "moving";
}

export function milepostToX(milepost, minimum, maximum, width) {
  const usable = Math.max(width - MAP_PADDING * 2, 1);
  const span = Math.max(Number(maximum) - Number(minimum), 0.001);
  const ratio = (Number(milepost) - Number(minimum)) / span;
  return MAP_PADDING + Math.min(1, Math.max(0, ratio)) * usable;
}

export function buildCorridorLayout(subdivision, width, top = 0) {
  const tracks = subdivision.tracks?.length
    ? subdivision.tracks
    : ["Main"];
  const trackY = Object.fromEntries(
    tracks.map((track, index) => [
      track,
      top + SUBDIVISION_HEADER + index * TRACK_GAP,
    ]),
  );
  return {
    ...subdivision,
    top,
    width,
    height: SUBDIVISION_HEADER + tracks.length * TRACK_GAP,
    trackY,
    xFor: (milepost) =>
      milepostToX(
        milepost,
        subdivision.minimum_milepost,
        subdivision.maximum_milepost,
        width,
      ),
  };
}

export function mapDimensions(subdivisions, zoom = 1) {
  const longestSpan = Math.max(
    1,
    ...subdivisions.map(
      (item) => item.maximum_milepost - item.minimum_milepost,
    ),
  );
  const width = Math.round(Math.max(1100, longestSpan * 72) * zoom);
  let top = 0;
  const corridors = subdivisions.map((subdivision) => {
    const corridor = buildCorridorLayout(subdivision, width, top);
    top += corridor.height + SUBDIVISION_GAP;
    return corridor;
  });
  return { width, height: Math.max(top, 260), corridors };
}

export function matchesFilters(asset, filters) {
  if (
    filters.subdivision !== "all" &&
    asset.subdivision !== filters.subdivision
  ) {
    return false;
  }
  if (filters.track !== "all" && (asset.track || "Main") !== filters.track) {
    return false;
  }
  const state = asset.type === "block" ? blockState(asset) : assetState(asset);
  if (filters.operational !== "all" && state !== filters.operational) {
    return false;
  }
  if (
    filters.security !== "all" &&
    normalize(asset.security_status) !== filters.security
  ) {
    return false;
  }
  if (
    filters.communications !== "all" &&
    normalize(asset.communications_status) !== filters.communications
  ) {
    return false;
  }
  return true;
}

export function controlledAssetKeys(device) {
  return (device?.relationships ?? []).map(
    (relationship) =>
      `${relationship.target_type}:${relationship.target_id}`,
  );
}

export function dispatchCommandState(commands, targetType, targetId) {
  const command = (commands ?? []).find(
    (item) =>
      item.target_type === targetType &&
      String(item.target_id) === String(targetId),
  );
  return command ? String(command.status || "").toLowerCase() : "";
}

export function activeMapConsequence(snapshot) {
  const isOpen = (item) =>
    !["closed", "resolved", "cleared"].includes(
      String(item?.status || "open").toLowerCase(),
    );
  const incident = (snapshot?.incidents ?? []).find(isOpen);
  if (incident) {
    return {
      severity: incident.severity || "High",
      title: incident.alert_type || "Active cyber incident",
      message: incident.message || "An active incident affects the territory.",
    };
  }
  const alert = (snapshot?.alerts ?? []).find(isOpen);
  if (alert) {
    return {
      severity: alert.severity || "High",
      title: alert.alert_type || "Active security alert",
      message: alert.message || "An active alert affects the territory.",
    };
  }

  const impact = snapshot?.operational_impact ?? {};
  const hasActiveImpact =
    Number(impact.affected_blocks || 0) > 0 ||
    Number(impact.delayed_trains || 0) > 0 ||
    Number(impact.unsafe_switches || 0) > 0 ||
    Number(impact.affected_crossings || 0) > 0 ||
    Number(impact.queued_commands || 0) > 0 ||
    Number(impact.active_restrictions || 0) > 0 ||
    Number(impact.dispatch_availability_percent ?? 100) < 100;
  if (!hasActiveImpact) return null;

  return (
    (snapshot?.timeline ?? []).find((event) =>
      ["critical", "high"].includes(String(event.severity).toLowerCase()),
    ) ||
    snapshot?.timeline?.[0] ||
    {
      severity: "Medium",
      title: "Operational impact active",
      message: impact.summary || "The territory is operating with restrictions.",
    }
  );
}

export function snapshotSignatures(snapshot) {
  const signature = {};
  const groups = [
    ["TRACK_BLOCK", snapshot.blocks],
    ["TRAIN", snapshot.trains],
    ["TRACK_SWITCH", snapshot.switches],
    ["GRADE_CROSSING", snapshot.crossings],
    ["OT_DEVICE", snapshot.devices],
  ];
  groups.forEach(([type, items]) => {
    (items ?? []).forEach((item) => {
      signature[`${type}:${item.id}`] = JSON.stringify([
        item.status,
        item.signal_aspect,
        item.speed,
        item.milepost,
        item.position,
        item.locked,
        item.gate_state,
        item.communications_status,
        item.security_status,
      ]);
    });
  });
  return signature;
}
