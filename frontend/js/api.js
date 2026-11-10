import { getToken, clearAuth } from "./state.js";

export class ApiError extends Error {
  constructor(status, code, message, fields = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.message = message;
    this.fields = fields;
  }
}

/**
 * Perform an HTTP request to the API.
 */
export async function request(method, path, body = null) {
  const headers = {
    "Content-Type": "application/json",
  };

  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const options = {
    method,
    headers,
  };

  if (body !== null && method !== "GET" && method !== "HEAD") {
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new ApiError(
      0,
      "network",
      "Can't reach Halfway. Check your connection and try again."
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null;
  }

  let data;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const errorObj = data && data.error ? data.error : {};
    const code = errorObj.code || (response.status === 401 ? "unauthorized" : "error");
    const message =
      errorObj.message ||
      (response.status >= 500
        ? "Something went wrong on our side. Try again in a moment."
        : "An unexpected error occurred.");
    const fields = errorObj.fields || null;

    // On 401 (except login and signup), clear token and redirect to login
    if (response.status === 401 && !path.includes("/api/auth/login") && !path.includes("/api/auth/signup")) {
      clearAuth();
      sessionStorage.setItem("halfway.flash_message", "Your session expired. Log in again.");
      window.location.hash = "#/login";
    }

    throw new ApiError(response.status, code, message, fields);
  }

  return data;
}
