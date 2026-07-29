import API from "../api";

export const getDigitalTwinMap = async () => {
  const response = await API.get("/digital-twin/map");
  return response.data;
};
