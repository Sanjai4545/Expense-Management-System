import { el, avatar, avatarStack, openDialog, toast } from "../ui.js";
import { formatPaise } from "../money.js";
import { request, ApiError } from "../api.js";
import { getUser, clearAuth } from "../state.js";

function getGreeting(name) {
  const hour = new Date().getHours();
  let timeStr = "morning";
  if (hour >= 12 && hour < 17) {
    timeStr = "afternoon";
  } else if (hour >= 17 || hour < 4) {
    timeStr = "evening";
  }
  return `Good ${timeStr}, ${name}`;
}

export async function renderGroups(container) {
  const currentUser = getUser() || { id: 0, name: "Friend", email: "" };

  // Site Header
  const header = el(
    "header",
    { className: "site-header" },
    el(
      "div",
      { className: "container site-header-inner" },
      el("a", { href: "#/groups", className: "wordmark" }, "Halfway"),
      el(
        "div",
        { className: "user-menu" },
        avatar(currentUser, 32),
        el("span", { style: { fontWeight: 600, fontSize: "var(--fs-sm)" } }, currentUser.name),
        el(
          "button",
          {
            type: "button",
            className: "btn btn-ghost btn-sm",
            onClick: () => {
              clearAuth();
              window.location.hash = "#/login";
            },
          },
          "Log out"
        )
      )
    )
  );

  const main = el("main", { className: "container", style: { paddingBottom: "var(--s7)" } });
  container.appendChild(header);
  container.appendChild(main);

  // Skeleton state while loading
  const skeletonView = el(
    "div",
    { style: { marginTop: "var(--s5)" } },
    el("div", { className: "skeleton", style: { height: "36px", width: "240px", marginBottom: "var(--s5)" } }),
    el(
      "div",
      { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "var(--s4)", marginBottom: "var(--s6)" } },
      el("div", { className: "skeleton", style: { height: "90px" } }),
      el("div", { className: "skeleton", style: { height: "90px" } })
    ),
    el(
      "div",
      { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "var(--s4)" } },
      el("div", { className: "skeleton", style: { height: "140px" } }),
      el("div", { className: "skeleton", style: { height: "140px" } })
    )
  );
  main.appendChild(skeletonView);

  try {
    const groups = await request("GET", "/api/groups");
    main.removeChild(skeletonView);

    // Calculate totals across all groups
    let totalOwed = 0;
    let totalOwing = 0;
    for (const g of groups) {
      if (g.my_balance_cents > 0) {
        totalOwed += g.my_balance_cents;
      } else if (g.my_balance_cents < 0) {
        totalOwing += Math.abs(g.my_balance_cents);
      }
    }

    // Greeting
    const greetingEl = el(
      "h1",
      { style: { margin: "var(--s6) 0 var(--s5)", fontSize: "var(--fs-2xl)" } },
      getGreeting(currentUser.name)
    );

    // Totals across all groups
    const totalsRow = el(
      "div",
      {
        style: {
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "var(--s4)",
          marginBottom: "var(--s6)",
        },
      },
      el(
        "div",
        { className: "card", style: { borderLeft: "4px solid var(--leaf)" } },
        el("div", { style: { fontSize: "var(--fs-sm)", color: "var(--slate)" } }, "You're owed"),
        el(
          "div",
          { className: "money font-display", style: { fontSize: "var(--fs-xl)", fontWeight: 700, color: "var(--leaf)", marginTop: "var(--s1)" } },
          totalOwed > 0 ? `+${formatPaise(totalOwed)}` : "₹0"
        )
      ),
      el(
        "div",
        { className: "card", style: { borderLeft: "4px solid var(--coral)" } },
        el("div", { style: { fontSize: "var(--fs-sm)", color: "var(--slate)" } }, "You owe"),
        el(
          "div",
          { className: "money font-display", style: { fontSize: "var(--fs-xl)", fontWeight: 700, color: "var(--coral)", marginTop: "var(--s1)" } },
          totalOwing > 0 ? `−${formatPaise(totalOwing)}` : "₹0"
        )
      )
    );

    // Section header with New Group button
    const sectionHeader = el(
      "div",
      {
        style: {
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "var(--s4)",
        },
      },
      el("h2", { style: { fontSize: "var(--fs-lg)" } }, "Your groups"),
      el(
        "button",
        {
          type: "button",
          className: "btn btn-primary",
          onClick: () => openNewGroupDialog(() => renderGroups(container)),
        },
        "New group"
      )
    );

    main.appendChild(greetingEl);
    main.appendChild(totalsRow);
    main.appendChild(sectionHeader);

    if (groups.length === 0) {
      // Empty state
      const emptyState = el(
        "div",
        { className: "empty-state card" },
        el(
          "svg",
          {
            className: "empty-state-svg",
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: "currentColor",
            strokeWidth: "1.5",
          },
          el("path", { d: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" }),
          el("circle", { cx: "9", cy: "7", r: "4" }),
          el("path", { d: "M23 21v-2a4 4 0 0 0-3-3.87" }),
          el("path", { d: "M16 3.13a4 4 0 0 1 0 7.75" })
        ),
        el("p", { className: "empty-state-text" }, "No groups yet. Create one for your next trip, flat, or dinner."),
        el(
          "button",
          {
            type: "button",
            className: "btn btn-primary",
            onClick: () => openNewGroupDialog(() => renderGroups(container)),
          },
          "Create a group"
        )
      );
      main.appendChild(emptyState);
    } else {
      // Grid of groups (1 col mobile, 2 col tablet, 3 col desktop)
      const grid = el("div", {
        style: {
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: "var(--s4)",
        },
      });

      for (const g of groups) {
        let balanceText = "All settled up";
        let balanceClass = "text-slate";
        if (g.my_balance_cents > 0) {
          balanceText = `You're owed ${formatPaise(g.my_balance_cents)}`;
          balanceClass = "text-leaf";
        } else if (g.my_balance_cents < 0) {
          balanceText = `You owe ${formatPaise(Math.abs(g.my_balance_cents))}`;
          balanceClass = "text-coral";
        }

        const groupCard = el(
          "a",
          {
            href: `#/groups/${g.id}`,
            className: "card",
            style: {
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              textDecoration: "none",
              color: "inherit",
              minHeight: "130px",
              cursor: "pointer",
            },
          },
          el("h3", { className: "truncate", style: { fontSize: "var(--fs-lg)", marginBottom: "var(--s2)" } }, g.name),
          el(
            "div",
            { style: { display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "auto" } },
            avatarStack(g.members_preview, 28, 4),
            el("span", { className: `money ${balanceClass}`, style: { fontWeight: 600, fontSize: "var(--fs-sm)" } }, balanceText)
          )
        );

        grid.appendChild(groupCard);
      }
      main.appendChild(grid);
    }
  } catch (err) {
    main.removeChild(skeletonView);
    const errState = el(
      "div",
      { className: "card empty-state" },
      el("p", { className: "text-coral" }, err.message || "Failed to load groups."),
      el(
        "button",
        {
          type: "button",
          className: "btn btn-primary",
          onClick: () => renderGroups(container),
        },
        "Try again"
      )
    );
    main.appendChild(errState);
  }
}

/**
 * Open new group dialog.
 */
function openNewGroupDialog(onCreated) {
  let isSubmitting = false;

  const nameInput = el("input", {
    type: "text",
    id: "group-name",
    className: "input",
    placeholder: "e.g. Goa Trip",
    required: true,
  });

  const errorMsg = el("div", {
    className: "input-error-msg",
    style: { display: "none" },
  });

  const submitBtn = el(
    "button",
    {
      type: "submit",
      className: "btn btn-primary",
    },
    "Create group"
  );

  let closeDialogFn;

  const form = el(
    "form",
    {
      onSubmit: async (e) => {
        e.preventDefault();
        if (isSubmitting) return;

        errorMsg.style.display = "none";
        errorMsg.textContent = "";
        nameInput.classList.remove("is-error");

        const name = nameInput.value.trim();
        if (!name) return;

        isSubmitting = true;
        submitBtn.disabled = true;
        submitBtn.textContent = "Creating…";

        try {
          const newGroup = await request("POST", "/api/groups", { name });
          toast("Group created");
          closeDialogFn();
          window.location.hash = `#/groups/${newGroup.id}`;
        } catch (err) {
          isSubmitting = false;
          submitBtn.disabled = false;
          submitBtn.textContent = "Create group";

          nameInput.classList.add("is-error");
          errorMsg.textContent = err.message || "Failed to create group.";
          errorMsg.style.display = "flex";
        }
      },
    },
    el(
      "div",
      { className: "form-group" },
      el("label", { className: "form-label", htmlFor: "group-name" }, "Group name"),
      nameInput,
      errorMsg
    ),
    el(
      "div",
      { className: "dialog-actions" },
      submitBtn
    )
  );

  closeDialogFn = openDialog(form, {
    title: "New group",
    onUnsavedCheck: () => nameInput.value.trim().length > 0,
  });

  setTimeout(() => nameInput.focus(), 50);
}
