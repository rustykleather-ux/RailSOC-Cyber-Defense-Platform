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
export const getExerciseRun = async (id, instructor = false) =>
  (await API.get(`/exercise-runs/${id}`, { params: { instructor } })).data;
export const exerciseRunAction = async (id, action) =>
  (await API.post(`/exercise-runs/${id}/${action}`)).data;
export const finishExerciseRun = async (id, confirmCancel = false) =>
  (await API.post(`/exercise-runs/${id}/finish`, {
    confirm_cancel: confirmCancel,
  })).data;
export const getExerciseWalkthrough = async (
  exerciseId,
  runId,
  instructor = false,
) =>
  (
    await API.get(`/exercises/${exerciseId}/walkthrough`, {
      params: { run_id: runId, instructor },
    })
  ).data;
export const revealExerciseWalkthrough = async (runId) =>
  (await API.post(`/exercise-runs/${runId}/walkthrough/reveal`)).data;
export const validateExercise = async (exerciseId) =>
  (
    await API.post(`/exercises/${exerciseId}/validate`, null, {
      params: { instructor: true },
    })
  ).data;
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
export const exerciseExportUrl = (id, instructor = false) =>
  `${API.defaults.baseURL}/exercises/${id}/export?instructor=${instructor}`;
