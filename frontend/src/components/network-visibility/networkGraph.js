const normalized = (value) => String(value || "").toLowerCase();

export const nodeMatchesFilters = (node, filters) => {
  const haystack = [
    node.display_name,
    node.hostname,
    node.ip_address,
    node.node_type,
    node.device_type,
    node.security_zone,
    node.location,
    node.status,
  ]
    .map(normalized)
    .join(" ");
  if (filters.search && !haystack.includes(normalized(filters.search))) return false;
  if (filters.zone && node.security_zone !== filters.zone) return false;
  if (filters.status && node.status !== filters.status) return false;
  if (filters.risk && node.risk_level !== filters.risk) return false;
  if (filters.protocol && !normalized(node.protocol).includes(normalized(filters.protocol)))
    return false;
  return true;
};

export const filterTopology = (topology, filters, collapsedZones = new Set()) => {
  const nodes = (topology.nodes || []).filter(
    (node) =>
      !collapsedZones.has(node.security_zone) && nodeMatchesFilters(node, filters),
  );
  const ids = new Set(nodes.map((node) => node.id));
  return {
    nodes,
    connections: (topology.connections || []).filter(
      (link) => ids.has(link.source_node_id) && ids.has(link.target_node_id),
    ),
  };
};

export const connectedNodeIds = (connections, nodeId) =>
  new Set(
    connections.flatMap((link) => {
      if (link.source_node_id === nodeId) return [link.target_node_id];
      if (link.target_node_id === nodeId) return [link.source_node_id];
      return [];
    }),
  );

export const autoLayout = (nodes, zones) => {
  const result = new Map();
  zones.forEach((zone, zoneIndex) => {
    const members = nodes.filter((node) => node.zone_id === zone.id);
    const baseX = (zoneIndex % 3) * 650;
    const baseY = Math.floor(zoneIndex / 3) * 540;
    members.forEach((node, index) => {
      result.set(node.id, {
        x: baseX + 36 + (index % 3) * 180,
        y: baseY + 84 + Math.floor(index / 3) * 118,
      });
    });
  });
  return result;
};

export const stateClass = (value) =>
  normalized(value).replaceAll(" ", "-").replaceAll("/", "-") || "unknown";

