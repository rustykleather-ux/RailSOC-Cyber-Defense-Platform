import API from "../api";

export const getExercises = async (params = {}) =>
  (await API.get("/exercises", { params })).data?.exercises || [];
export const createExercise = (data) => API.post("/exercises", data);
export const updateExercise = (id, data) => API.put(`/exercises/${id}`, data);
export const deleteExercise = (id) => API.delete(`/exercises/${id}`);
export const cloneExercise = (id, name) =>
  API.post(`/exercises/${id}/clone`, { name });
export const createExerciseRun = async (exerciseId) =>
  (await API.post("/exercise-runs", { exercise_id: exerciseId })).data;
export const getExerciseRuns = async () =>
  (await API.get("/exercise-runs")).data?.runs || [];
export const clearExerciseRuns = async () =>
  (await API.delete("/exercise-runs")).data;
export const getExerciseRun = async (id) =>
  (await API.get(`/exercise-runs/${id}`)).data;
export const exerciseRunAction = async (id, action) =>
  (await API.post(`/exercise-runs/${id}/${action}`)).data;
export const createCheckpoint = async (id, name) =>
  (await API.post(`/exercise-runs/${id}/checkpoints`, { name })).data;
export const restoreCheckpoint = async (runId, checkpointId) =>
  (await API.post(
    `/exercise-runs/${runId}/checkpoints/${checkpointId}/restore`,
  )).data;
export const requestExerciseHint = async (id) =>
  (await API.post(`/exercise-runs/${id}/hints`)).data;
export const getAfterActionReport = async (id) =>
  (await API.get(`/exercise-runs/${id}/after-action-report`)).data;
export const reportDownloadUrl = (id, format) =>
  `${API.defaults.baseURL}/exercise-runs/${id}/after-action-report?format=${format}`;
export const exerciseExportUrl = (id) =>
  `${API.defaults.baseURL}/exercises/${id}/export`;
