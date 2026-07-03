import API from "../api";

export const getIncidents = () => {
  return API.get("/incidents");
};

export const acknowledgeIncidentRequest = (incidentId) => {
  return API.post(`/incidents/${incidentId}/acknowledge`);
};