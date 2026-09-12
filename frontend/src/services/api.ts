import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request Interceptor: Attach Session Token
apiClient.interceptors.request.use((config) => {
  const sessionId = localStorage.getItem("kinostats_session_id");
  if (sessionId) {
    config.headers["X-Session-ID"] = sessionId;
  }
  return config;
});

// Response Interceptor: Persist Session Token
apiClient.interceptors.response.use((response) => {
  const sessionToken =
    response.headers["x-session-id"] || response.data?.sessionToken;
  if (sessionToken) {
    localStorage.setItem("kinostats_session_id", sessionToken);
  }
  return response;
});