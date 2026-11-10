import { isAuthenticated } from "./state.js";

const routes = {};

export function registerRoute(pattern, handler, title = "Halfway") {
  routes[pattern] = { handler, title };
}

function parseHash(hash) {
  const path = hash.replace(/^#/, "") || "/";
  return path.split("?")[0];
}

export async function navigate() {
  const appContainer = document.getElementById("app");
  if (!appContainer) return;

  const currentPath = parseHash(window.location.hash);
  const authed = isAuthenticated();

  // Auth guards
  if (!authed && currentPath !== "/login" && currentPath !== "/signup") {
    window.location.hash = "#/login";
    return;
  }
  if (authed && (currentPath === "/login" || currentPath === "/signup" || currentPath === "/")) {
    window.location.hash = "#/groups";
    return;
  }

  // Route matching
  let matchedHandler = null;
  let params = {};
  let title = "Halfway";

  for (const [pattern, route] of Object.entries(routes)) {
    if (pattern === currentPath) {
      matchedHandler = route.handler;
      title = route.title;
      break;
    }
    // Pattern matching with :param (e.g. /groups/:id)
    const patternParts = pattern.split("/");
    const pathParts = currentPath.split("/");

    if (patternParts.length === pathParts.length) {
      let match = true;
      const extractedParams = {};
      for (let i = 0; i < patternParts.length; i++) {
        if (patternParts[i].startsWith(":")) {
          const paramName = patternParts[i].slice(1);
          extractedParams[paramName] = pathParts[i];
        } else if (patternParts[i] !== pathParts[i]) {
          match = false;
          break;
        }
      }
      if (match) {
        matchedHandler = route.handler;
        params = extractedParams;
        title = route.title;
        break;
      }
    }
  }

  if (!matchedHandler) {
    // Unknown route
    window.location.hash = authed ? "#/groups" : "#/login";
    return;
  }

  document.title = title;
  // Clear previous content
  while (appContainer.firstChild) {
    appContainer.removeChild(appContainer.firstChild);
  }

  try {
    await matchedHandler(appContainer, params);
  } catch (err) {
    console.error("Route render error:", err);
  }
}

export function startRouter() {
  window.addEventListener("hashchange", navigate);
  navigate();
}
