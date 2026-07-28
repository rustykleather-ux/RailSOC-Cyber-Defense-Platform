import API from "../api";

export const getOperationalImpact = async () => {
  const response = await API.get("/operations/impact");
  return response.data;
};

export const getOperationsTimeline = async (limit = 100) => {
  const response = await API.get("/operations/timeline", {
    params: { limit },
  });
  return response.data?.events || [];
};
