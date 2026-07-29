import API from "../api";

export async function getDispatchWorkspace() {
  const [status, commands, routes, restrictions, map] = await Promise.all([
    API.get("/dispatch/status"),
    API.get("/dispatch/commands"),
    API.get("/dispatch/routes"),
    API.get("/dispatch/restrictions", { params: { active: true } }),
    API.get("/digital-twin/map"),
  ]);
  return {
    status: status.data,
    commands: commands.data?.commands || [],
    routes: routes.data?.routes || [],
    restrictions: restrictions.data?.restrictions || [],
    map: map.data,
  };
}

export const submitDispatchCommand = (data) =>
  API.post("/dispatch/commands", data);
export const cancelDispatchCommand = (id) =>
  API.post(`/dispatch/commands/${id}/cancel`, { requested_by: "Dispatcher" });
export const retryDispatchCommand = (id) =>
  API.post(`/dispatch/commands/${id}/retry`, { requested_by: "Dispatcher" });
export const submitDispatchRoute = (data) =>
  API.post("/dispatch/routes", data);
export const submitRestriction = (data) =>
  API.post("/dispatch/restrictions", data);
export const clearRestriction = (id) =>
  API.post(`/dispatch/restrictions/${id}/clear`, {
    requested_by: "Dispatcher",
  });
export const submitRecoveryAction = (data) =>
  API.post("/dispatch/recovery-actions", data);
