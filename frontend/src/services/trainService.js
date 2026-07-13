import API from "../api";

export const getTrains = async () => {
  const response = await API.get("/trains");
  return response.data;
};

export const startSimulation = async () => {
  return API.post("/train-simulation/start");
};

export const stopSimulation = async () => {
  return API.post("/train-simulation/stop");
};

export const resetSimulation = async () => {
  return API.post("/train-simulation/reset");
};