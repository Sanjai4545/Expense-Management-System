import { registerRoute, startRouter } from "./router.js";
import { renderAuth } from "./views/auth.js";
import { renderGroups } from "./views/groups.js";
import { renderGroup } from "./views/group.js";

// Wire routes
registerRoute("/login", (c, p) => renderAuth(c, p, false), "Log in · Halfway");
registerRoute("/signup", (c, p) => renderAuth(c, p, true), "Create account · Halfway");
registerRoute("/groups", (c, p) => renderGroups(c, p), "Your groups · Halfway");
registerRoute("/groups/:id", (c, p) => renderGroup(c, p), "Group · Halfway");

// Boot
window.addEventListener("DOMContentLoaded", () => {
  startRouter();
});
