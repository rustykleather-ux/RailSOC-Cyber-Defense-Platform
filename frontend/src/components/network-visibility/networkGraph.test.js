import assert from "node:assert/strict";
import test from "node:test";
import {
  autoLayout,
  connectedNodeIds,
  filterTopology,
  nodeMatchesFilters,
  stateClass,
} from "./networkGraph.js";

const nodes = [
  {
    id: 1,
    zone_id: 1,
    display_name: "Signal Controller 14A",
    hostname: "sig-14a",
    ip_address: "192.168.50.10",
    node_type: "Controller",
    device_type: "Signal Controller",
    security_zone: "Railroad OT",
    location: "East Territory",
    status: "Compromised",
    risk_level: "Critical",
    protocol: "DNP3",
  },
  {
    id: 2,
    zone_id: 2,
    display_name: "Dispatch Firewall",
    hostname: "dispatch-fw-01",
    ip_address: "10.20.0.1",
    node_type: "Firewall",
    device_type: "Firewall",
    security_zone: "Dispatch Center",
    location: "Dispatch",
    status: "Healthy",
    risk_level: "Low",
    protocol: "HTTPS",
  },
];
const connections = [
  { id: 8, source_node_id: 1, target_node_id: 2, protocol: "DNP3" },
];

test("network search and filters match IP, type, zone, status, and protocol", () => {
  assert.equal(nodeMatchesFilters(nodes[0], {
    search: "192.168.50",
    zone: "Railroad OT",
    status: "Compromised",
    risk: "Critical",
    protocol: "dnp3",
  }), true);
  assert.equal(nodeMatchesFilters(nodes[0], {
    search: "",
    zone: "Dispatch Center",
    status: "",
    risk: "",
    protocol: "",
  }), false);
});

test("collapsed zones and filtered nodes remove dangling connections", () => {
  const result = filterTopology(
    { nodes, connections },
    { search: "", zone: "", status: "", risk: "", protocol: "" },
    new Set(["Dispatch Center"]),
  );
  assert.deepEqual(result.nodes.map((node) => node.id), [1]);
  assert.equal(result.connections.length, 0);
});

test("path and connected node highlighting inputs are deterministic", () => {
  assert.deepEqual([...connectedNodeIds(connections, 1)], [2]);
  assert.equal(stateClass("High latency"), "high-latency");
  const layout = autoLayout(nodes, [
    { id: 1, name: "Railroad OT" },
    { id: 2, name: "Dispatch Center" },
  ]);
  assert.ok(layout.get(1).x < layout.get(2).x);
  assert.deepEqual(layout, autoLayout(nodes, [
    { id: 1, name: "Railroad OT" },
    { id: 2, name: "Dispatch Center" },
  ]));
});

