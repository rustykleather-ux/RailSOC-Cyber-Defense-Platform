import API from "../api";

export const getNetworkTopology = async (eventLimit = 100) =>
  (await API.get("/api/network/topology", { params: { event_limit: eventLimit } }))
    .data;

export const getNetworkNode = async (id) =>
  (await API.get(`/api/network/nodes/${id}`)).data;

export const getNetworkConnection = async (id) =>
  (await API.get(`/api/network/connections/${id}`)).data;

export const traceNetworkPath = async (sourceNodeId, destinationNodeId) =>
  (
    await API.post("/api/network/path/trace", {
      source_node_id: sourceNodeId,
      destination_node_id: destinationNodeId,
    })
  ).data;

export const saveNetworkLayout = async (positions) =>
  (await API.post("/api/network/layout", { positions })).data;

export const runNetworkNodeAction = async (id, action) =>
  (await API.post(`/api/network/nodes/${id}/${action}`)).data;

export const runNetworkConnectionAction = async (id, action) =>
  (await API.post(`/api/network/connections/${id}/${action}`)).data;

export const runNetworkSimulation = async (
  simulationType,
  sourceNodeId = null,
  targetNodeId = null,
) =>
  (
    await API.post("/api/network/simulate", {
      simulation_type: simulationType,
      source_node_id: sourceNodeId,
      target_node_id: targetNodeId,
    })
  ).data;

export const resetNetworkSimulation = async () =>
  (await API.post("/api/network/reset")).data;

export const networkWebSocketUrl = () => {
  const apiUrl = new URL(API.defaults.baseURL);
  const scheme = apiUrl.protocol === "https:" ? "wss:" : "ws:";
  return `${scheme}//${apiUrl.host}/ws/network`;
};

