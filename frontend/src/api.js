import axios from "axios";

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

const API = axios.create({
  baseURL: API_BASE_URL,
});

export default API;
