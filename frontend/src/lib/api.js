const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  const text = await response.text();
  return text ? { detail: text } : null;
}

function extractMessage(payload) {
  if (!payload) return "Request failed";
  if (typeof payload === "string") return payload;
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((item) => item.msg || item.message || "Invalid input").join(", ");
  }
  return payload.message || "Request failed";
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const payload = await parseResponse(response);

  if (!response.ok) {
    throw new ApiError(extractMessage(payload), response.status, payload);
  }

  return payload;
}

export function registerUser(payload) {
  return request("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function loginUser(payload) {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function logoutUser() {
  return request("/auth/logout", {
    method: "POST",
  });
}

export function getCurrentUser() {
  return request("/auth/me");
}

export function getUserMemory() {
  return request("/user-memory");
}

export function getTripById(tripId) {
  return request(`/trips/${tripId}`);
}

export function updateUserMemory(payload) {
  return request("/update-memory", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function generateTrip(payload) {
  return request("/generate-trip", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getDestinationSuggestions(query, limit = 6) {
  const params = new URLSearchParams({
    q: query,
    limit: String(limit),
  });
  return request(`/destination-suggestions?${params.toString()}`);
}
