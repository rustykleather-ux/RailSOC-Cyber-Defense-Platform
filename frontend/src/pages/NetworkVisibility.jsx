import {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Activity,
  Bot,
  ChevronDown,
  ChevronRight,
  CircleOff,
  Expand,
  Filter,
  LocateFixed,
  Network,
  Pause,
  Play,
  Radio,
  RotateCcw,
  Route,
  Save,
  Search,
  Server,
  Shield,
  ShieldAlert,
  Workflow,
  X,
  Zap,
} from "lucide-react";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getNetworkConnection,
  getNetworkNode,
  getNetworkTopology,
  networkWebSocketUrl,
  resetNetworkSimulation,
  runNetworkConnectionAction,
  runNetworkNodeAction,
  runNetworkSimulation,
  saveNetworkLayout,
  traceNetworkPath,
} from "../services/networkService";
import {
  autoLayout,
  connectedNodeIds,
  filterTopology,
  stateClass,
} from "../components/network-visibility/networkGraph";
import "./NetworkVisibility.css";

const iconFor = (type) => {
  const value = String(type || "").toLowerCase();
  if (value.includes("firewall") || value.includes("ids")) return Shield;
  if (value.includes("radio") || value.includes("router")) return Radio;
  if (value.includes("controller") || value.includes("scada")) return Bot;
  if (value.includes("external") || value.includes("cloud")) return ShieldAlert;
  return Server;
};

const NetworkAssetNode = memo(({ data, selected }) => {
  const Icon = iconFor(data.node.node_type);
  return (
    <div
      className={`network-asset-node ${stateClass(data.node.status)} ${
        selected ? "selected" : ""
      } ${data.highlighted ? "highlighted" : ""}`}
    >
      <Handle type="target" position={Position.Left} />
      <div className="network-node-icon">
        <Icon size={18} />
      </div>
      <div>
        <strong>{data.node.display_name}</strong>
        <span>{data.node.hostname || data.node.device_type}</span>
        <small>
          {data.node.status} · {data.node.risk_level}
        </small>
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
});

const ZoneNode = memo(({ data }) => (
  <div className="network-zone-node" style={{ "--zone-color": data.zone.color_key }}>
    <strong>{data.zone.name}</strong>
    <span>
      {data.zone.zone_type} · {data.zone.trust_level} trust
    </span>
  </div>
));

const nodeTypes = { asset: NetworkAssetNode, zone: ZoneNode };

const emptyTopology = {
  nodes: [],
  connections: [],
  zones: [],
  events: [],
  summary: {},
};

const simulationOptions = [
  ["high_latency", "High latency"],
  ["packet_loss", "Packet loss"],
  ["fiber_failure", "Fiber failure"],
  ["radio_outage", "Radio outage"],
  ["unauthorized_remote_access", "Unauthorized remote access"],
  ["network_scan", "Network scan"],
  ["lateral_movement", "Lateral movement"],
  ["firewall_block", "Firewall block"],
];

function NetworkVisibilityCanvas() {
  const [topology, setTopology] = useState(emptyTopology);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [filters, setFilters] = useState({
    search: "",
    zone: "",
    status: "",
    risk: "",
    protocol: "",
  });
  const [collapsedZones, setCollapsedZones] = useState(new Set());
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedConnection, setSelectedConnection] = useState(null);
  const [pathSource, setPathSource] = useState("");
  const [pathTarget, setPathTarget] = useState("");
  const [pathResult, setPathResult] = useState(null);
  const [trafficEnabled, setTrafficEnabled] = useState(true);
  const [suspiciousOnly, setSuspiciousOnly] = useState(false);
  const [trafficSpeed, setTrafficSpeed] = useState(1);
  const [status, setStatus] = useState("Connecting");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const graphRef = useRef(null);
  const flowRef = useRef(null);

  const loadTopology = useCallback(async () => {
    try {
      const data = await getNetworkTopology(150);
      setTopology(data);
      setStatus("Polling");
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Network topology is unavailable.");
      setStatus("Offline");
    }
  }, []);

  useEffect(() => {
    loadTopology();
    let socket;
    let pollTimer;
    try {
      socket = new WebSocket(networkWebSocketUrl());
      socket.onopen = () => setStatus("Live");
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (
          message.type === "network_snapshot" &&
          message.simulation_only === true &&
          message.topology
        ) {
          setTopology(message.topology);
          setError("");
        }
      };
      socket.onerror = () => setStatus("Polling");
      socket.onclose = () => {
        setStatus("Polling");
        pollTimer = window.setInterval(loadTopology, 5000);
      };
    } catch {
      pollTimer = window.setInterval(loadTopology, 5000);
    }
    return () => {
      if (socket) socket.close();
      if (pollTimer) window.clearInterval(pollTimer);
    };
  }, [loadTopology]);

  const visible = useMemo(
    () => filterTopology(topology, filters, collapsedZones),
    [topology, filters, collapsedZones],
  );
  const pathNodeIds = useMemo(
    () => new Set((pathResult?.hops || []).map((hop) => hop.id)),
    [pathResult],
  );
  const pathConnectionIds = useMemo(
    () => new Set(pathResult?.connection_ids || []),
    [pathResult],
  );
  const connectedIds = useMemo(
    () =>
      selectedNode
        ? connectedNodeIds(topology.connections || [], selectedNode.id)
        : new Set(),
    [selectedNode, topology.connections],
  );

  useEffect(() => {
    const positions = autoLayout(topology.nodes || [], topology.zones || []);
    setNodes((current) => {
      const currentPositions = new Map(current.map((node) => [node.id, node.position]));
      const zoneNodes = (topology.zones || []).map((zone, index) => ({
        id: `zone-${zone.id}`,
        type: "zone",
        position: { x: (index % 3) * 650, y: Math.floor(index / 3) * 540 },
        data: { zone },
        selectable: false,
        draggable: false,
        connectable: false,
        style: { width: 610, height: 490, zIndex: -1 },
      }));
      const assetNodes = visible.nodes.map((node) => ({
        id: String(node.id),
        type: "asset",
        position:
          currentPositions.get(String(node.id)) ||
          node.position ||
          positions.get(node.id) ||
          { x: 0, y: 0 },
        data: {
          node,
          highlighted:
            pathNodeIds.has(node.id) ||
            connectedIds.has(node.id) ||
            selectedNode?.id === node.id,
        },
      }));
      return [...zoneNodes, ...assetNodes];
    });
  }, [
    topology.nodes,
    topology.zones,
    visible.nodes,
    pathNodeIds,
    connectedIds,
    selectedNode,
    setNodes,
  ]);

  useEffect(() => {
    setEdges(
      visible.connections.map((link) => ({
        id: String(link.id),
        source: String(link.source_node_id),
        target: String(link.target_node_id),
        label: `${link.protocol}${link.port ? `:${link.port}` : ""}`,
        animated:
          trafficEnabled &&
          (!suspiciousOnly ||
            link.status === "Suspicious" ||
            link.risk_level === "High"),
        markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
        className: `${stateClass(link.status)} ${
          pathConnectionIds.has(link.id) ? "path-highlight" : ""
        }`,
        style: { "--traffic-speed": `${Math.max(0.25, 2 / trafficSpeed)}s` },
        data: { link },
      })),
    );
  }, [
    visible.connections,
    trafficEnabled,
    suspiciousOnly,
    trafficSpeed,
    pathConnectionIds,
    setEdges,
  ]);

  const selectNode = useCallback(async (_, flowNode) => {
    if (flowNode.type !== "asset") return;
    setSelectedConnection(null);
    try {
      setSelectedNode(await getNetworkNode(Number(flowNode.id)));
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to load node details.");
    }
  }, []);

  const selectEdge = useCallback(async (_, flowEdge) => {
    setSelectedNode(null);
    try {
      setSelectedConnection(await getNetworkConnection(Number(flowEdge.id)));
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail || "Unable to load connection details.",
      );
    }
  }, []);

  const execute = async (operation) => {
    setBusy(true);
    setError("");
    try {
      await operation();
      await loadTopology();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Simulation action failed.");
    } finally {
      setBusy(false);
    }
  };

  const trace = () =>
    execute(async () => {
      if (!pathSource || !pathTarget || pathSource === pathTarget) {
        throw new Error("Choose two different path endpoints.");
      }
      setPathResult(await traceNetworkPath(Number(pathSource), Number(pathTarget)));
    });

  const layout = () => {
    const positions = autoLayout(topology.nodes, topology.zones);
    setNodes((current) =>
      current.map((node) =>
        node.type === "asset"
          ? { ...node, position: positions.get(Number(node.id)) || node.position }
          : node,
      ),
    );
    window.setTimeout(() => flowRef.current?.fitView({ padding: 0.08 }), 30);
  };

  const saveLayout = () =>
    execute(() =>
      saveNetworkLayout(
        nodes
          .filter((node) => node.type === "asset")
          .map((node) => ({ id: Number(node.id), ...node.position })),
      ),
    );

  const toggleZone = (zoneName) =>
    setCollapsedZones((current) => {
      const next = new Set(current);
      if (next.has(zoneName)) next.delete(zoneName);
      else next.add(zoneName);
      return next;
    });

  const allStatuses = [...new Set(topology.nodes.map((node) => node.status))];
  const allRisks = [...new Set(topology.nodes.map((node) => node.risk_level))];
  const allProtocols = [...new Set(topology.nodes.map((node) => node.protocol))];

  return (
    <section className="network-visibility-page" ref={graphRef}>
      <header className="network-page-header">
        <div>
          <span className="eyebrow">Simulation-backed IT / OT architecture</span>
          <h1>Network Visibility</h1>
          <p>
            Live relationships from TrackSentinel state and generated telemetry.
            No real network discovery or packet capture.
          </p>
        </div>
        <div className={`network-live-badge ${status.toLowerCase()}`}>
          <Activity size={15} /> {status}
        </div>
      </header>

      <div className="network-summary-grid">
        {[
          ["Assets", topology.summary.nodes || 0, Network],
          ["Connections", topology.summary.connections || 0, Workflow],
          ["Degraded assets", topology.summary.degraded_nodes || 0, CircleOff],
          ["Suspicious events", topology.summary.suspicious_events || 0, ShieldAlert],
        ].map(([label, value, Icon]) => (
          <article key={label}>
            <Icon size={20} />
            <div>
              <strong>{value}</strong>
              <span>{label}</span>
            </div>
          </article>
        ))}
      </div>

      {error && (
        <div className="network-error">
          <ShieldAlert size={18} />
          <span>{error.message || error}</span>
          <button onClick={() => setError("")} aria-label="Dismiss error">
            <X size={16} />
          </button>
        </div>
      )}

      <div className="network-toolbar">
        <label className="network-search">
          <Search size={17} />
          <input
            value={filters.search}
            onChange={(event) =>
              setFilters((current) => ({ ...current, search: event.target.value }))
            }
            placeholder="Search hostname, IP, type, zone, location…"
          />
        </label>
        {[
          ["zone", "All zones", topology.zones.map((zone) => zone.name)],
          ["status", "All states", allStatuses],
          ["risk", "All risks", allRisks],
          ["protocol", "All protocols", allProtocols],
        ].map(([key, label, values]) => (
          <label className="network-select" key={key}>
            <Filter size={14} />
            <select
              value={filters[key]}
              onChange={(event) =>
                setFilters((current) => ({ ...current, [key]: event.target.value }))
              }
            >
              <option value="">{label}</option>
              {values.filter(Boolean).map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>
        ))}
        <button onClick={() => flowRef.current?.fitView({ padding: 0.08 })}>
          <LocateFixed size={16} /> Fit
        </button>
        <button onClick={layout}>
          <Workflow size={16} /> Auto-layout
        </button>
        <button disabled={busy} onClick={saveLayout}>
          <Save size={16} /> Save
        </button>
        <button onClick={() => graphRef.current?.requestFullscreen?.()}>
          <Expand size={16} /> Full screen
        </button>
      </div>

      <div className="network-zone-toggles">
        {topology.zones.map((zone) => (
          <button key={zone.id} onClick={() => toggleZone(zone.name)}>
            {collapsedZones.has(zone.name) ? (
              <ChevronRight size={14} />
            ) : (
              <ChevronDown size={14} />
            )}
            <i style={{ background: zone.color_key }} />
            {zone.name}
          </button>
        ))}
      </div>

      <div className="network-workspace">
        <div className="network-graph">
          {topology.nodes.length === 0 && !error ? (
            <div className="network-empty">Waiting for simulated topology…</div>
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={selectNode}
              onEdgeClick={selectEdge}
              onPaneClick={() => {
                setSelectedNode(null);
                setSelectedConnection(null);
              }}
              onInit={(instance) => {
                flowRef.current = instance;
                instance.fitView({ padding: 0.08 });
              }}
              nodeTypes={nodeTypes}
              minZoom={0.2}
              maxZoom={2.2}
              fitView
              onlyRenderVisibleElements
            >
              <Background color="#24324b" gap={28} />
              <Controls />
              <MiniMap
                pannable
                zoomable
                nodeColor={(node) =>
                  node.type === "zone"
                    ? node.data.zone.color_key
                    : node.data.node.status === "Compromised"
                      ? "#ef4444"
                      : "#38bdf8"
                }
              />
            </ReactFlow>
          )}
          <div className="traffic-controls">
            <button onClick={() => setTrafficEnabled((value) => !value)}>
              {trafficEnabled ? <Pause size={14} /> : <Play size={14} />}
              Traffic
            </button>
            <label>
              <input
                type="checkbox"
                checked={suspiciousOnly}
                onChange={(event) => setSuspiciousOnly(event.target.checked)}
              />
              Suspicious only
            </label>
            <label>
              Speed
              <input
                type="range"
                min="0.5"
                max="3"
                step="0.5"
                value={trafficSpeed}
                onChange={(event) => setTrafficSpeed(Number(event.target.value))}
              />
            </label>
          </div>
        </div>

        <aside className="network-side-panel">
          <div className="network-panel-section">
            <h3>
              <Route size={17} /> Path trace
            </h3>
            <select value={pathSource} onChange={(event) => setPathSource(event.target.value)}>
              <option value="">Source node</option>
              {topology.nodes.map((node) => (
                <option value={node.id} key={node.id}>{node.display_name}</option>
              ))}
            </select>
            <select value={pathTarget} onChange={(event) => setPathTarget(event.target.value)}>
              <option value="">Destination node</option>
              {topology.nodes.map((node) => (
                <option value={node.id} key={node.id}>{node.display_name}</option>
              ))}
            </select>
            <button disabled={busy || !pathSource || !pathTarget} onClick={trace}>
              Trace deterministic path
            </button>
            {pathResult && (
              <div className="path-result">
                <strong>{pathResult.path_status}</strong>
                <span>{pathResult.hops.length} hops</span>
                <span>{pathResult.total_latency_ms} ms</span>
                <span>{pathResult.total_packet_loss}% loss</span>
                <small>{pathResult.zones_crossed.join(" → ")}</small>
              </div>
            )}
          </div>

          <div className="network-panel-section">
            <h3>
              <Zap size={17} /> Simulation controls
            </h3>
            <div className="simulation-control-grid">
              {simulationOptions.map(([key, label]) => (
                <button
                  key={key}
                  disabled={busy}
                  onClick={() => execute(() => runNetworkSimulation(key))}
                >
                  {label}
                </button>
              ))}
            </div>
            <button
              className="restore-button"
              disabled={busy}
              onClick={() => execute(resetNetworkSimulation)}
            >
              <RotateCcw size={15} /> Restore network baseline
            </button>
          </div>
        </aside>
      </div>

      {(selectedNode || selectedConnection) && (
        <aside className="network-details-drawer">
          <button
            className="drawer-close"
            onClick={() => {
              setSelectedNode(null);
              setSelectedConnection(null);
            }}
            aria-label="Close details"
          >
            <X size={18} />
          </button>
          {selectedNode ? (
            <NodeDetails
              node={selectedNode}
              busy={busy}
              onAction={(action) =>
                execute(async () => {
                  setSelectedNode(await runNetworkNodeAction(selectedNode.id, action));
                })
              }
            />
          ) : (
            <ConnectionDetails
              connection={selectedConnection}
              busy={busy}
              onAction={(action) =>
                execute(async () => {
                  setSelectedConnection(
                    await runNetworkConnectionAction(selectedConnection.id, action),
                  );
                })
              }
            />
          )}
        </aside>
      )}

      <section className="network-history">
        <div>
          <span className="eyebrow">Historical simulated telemetry</span>
          <h2>Recent network events</h2>
        </div>
        {topology.events.length ? (
          <div className="network-event-table">
            {topology.events.slice(0, 50).map((event) => (
              <article key={event.id} className={event.is_suspicious ? "suspicious" : ""}>
                <time>{event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : "—"}</time>
                <strong>{event.event_type.replaceAll("_", " ")}</strong>
                <span>{event.protocol || "Internal"}</span>
                <p>{event.description}</p>
                <b>{event.severity}</b>
              </article>
            ))}
          </div>
        ) : (
          <p className="network-empty-history">No simulated network events yet.</p>
        )}
      </section>
    </section>
  );
}

function DetailRows({ rows }) {
  return (
    <dl>
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value ?? "—"}</dd>
        </div>
      ))}
    </dl>
  );
}

function NodeDetails({ node, busy, onAction }) {
  return (
    <>
      <span className="eyebrow">{node.security_zone}</span>
      <h2>{node.display_name}</h2>
      <div className={`detail-state ${stateClass(node.status)}`}>{node.status}</div>
      <DetailRows
        rows={[
          ["Hostname", node.hostname],
          ["IP address", node.ip_address],
          ["Type", `${node.node_type} / ${node.device_type}`],
          ["Segment", node.network_segment],
          ["Location", node.location],
          ["Health", node.health],
          ["Risk", node.risk_level],
          ["Criticality", node.criticality],
          ["Vendor / model", `${node.vendor} ${node.model}`],
          ["Firmware", node.firmware_version],
          ["Operating system", node.operating_system],
          ["Protocols", node.protocol],
          ["Connected assets", node.connected_node_ids?.length || 0],
          ["Active alerts", node.active_alerts || 0],
          ["Open incidents", node.open_incidents || 0],
          ["Last seen", node.last_seen ? new Date(node.last_seen).toLocaleString() : "—"],
        ]}
      />
      <div className="drawer-actions">
        <button disabled={busy} onClick={() => onAction("investigate")}>Investigate</button>
        <button disabled={busy} onClick={() => onAction("isolate")}>Isolate</button>
        <button disabled={busy} onClick={() => onAction("restore")}>Restore</button>
      </div>
    </>
  );
}

function ConnectionDetails({ connection, busy, onAction }) {
  return (
    <>
      <span className="eyebrow">Simulated connection</span>
      <h2>{connection.source_name} → {connection.target_name}</h2>
      <div className={`detail-state ${stateClass(connection.status)}`}>
        {connection.status}
      </div>
      <DetailRows
        rows={[
          ["Type", connection.connection_type],
          ["Direction", connection.direction],
          ["Protocol / port", `${connection.protocol}${connection.port ? `:${connection.port}` : ""}`],
          ["Latency", `${connection.latency_ms} ms`],
          ["Packet loss", `${connection.packet_loss_percent}%`],
          ["Bandwidth", `${connection.bandwidth_mbps} Mbps`],
          ["Encrypted", connection.encrypted ? "Yes" : "No"],
          ["Boundary crossing", connection.security_boundary_crossing ? "Yes" : "No"],
          ["Risk", connection.risk_level],
          ["Last activity", connection.last_activity ? new Date(connection.last_activity).toLocaleString() : "—"],
        ]}
      />
      <div className="drawer-actions">
        <button disabled={busy} onClick={() => onAction("fail")}>Simulate failure</button>
        <button disabled={busy} onClick={() => onAction("restore")}>Restore</button>
      </div>
    </>
  );
}

export default function NetworkVisibility() {
  return (
    <ReactFlowProvider>
      <NetworkVisibilityCanvas />
    </ReactFlowProvider>
  );
}

