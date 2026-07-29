import API from "../api";


export const getDevices = () => {
    return API.get("/devices");
};

export const createDevice = (device) => API.post("/devices", device);
export const getDeviceTypes = () => API.get("/device-types");
export const createDeviceType = (deviceType) =>
  API.post("/device-types", deviceType);
export const getCapabilities = () => API.get("/capabilities");
export const getRelationshipTargets = () =>
  API.get("/relationship-targets");
export const addRelationship = (deviceId, relationship) =>
  API.post(`/devices/${deviceId}/relationships`, relationship);
export const deleteRelationship = (deviceId, relationshipId) =>
  API.delete(`/devices/${deviceId}/relationships/${relationshipId}`);
