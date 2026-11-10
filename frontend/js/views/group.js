import {
  el,
  avatar,
  avatarStack,
  openDialog,
  confirmDialog,
  toast,
  formatDate,
  formatMonthYear,
} from "../ui.js";
import { formatPaise } from "../money.js";
import { request, ApiError } from "../api.js";
import { getUser, clearAuth } from "../state.js";
import { openMemberDialog } from "./memberDialog.js";
import { openPaymentDialog } from "./paymentDialog.js";
import { openExpenseDialog } from "./expenseDialog.js";

export async function renderGroup(container, params) {
  const groupId = parseInt(params.id, 10);
  const currentUser = getUser() || { id: 0, name: "User" };

  // Site Header
  const siteHeader = el(
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

  const main = el("main", { className: "container has-mobile-bottom-bar", style: { paddingBottom: "var(--s7)" } });
  container.appendChild(siteHeader);
  container.appendChild(main);

  // Skeleton view
  const skeletonView = el(
    "div",
    { style: { marginTop: "var(--s5)" } },
    el("div", { className: "skeleton", style: { height: "24px", width: "120px", marginBottom: "var(--s4)" } }),
    el("div", { className: "skeleton", style: { height: "48px", width: "320px", marginBottom: "var(--s6)" } }),
    el("div", { className: "skeleton", style: { height: "240px", marginBottom: "var(--s4)" } })
  );
  main.appendChild(skeletonView);

  async function loadData() {
    try {
      const [group, balancesData, activity] = await Promise.all([
        request("GET", `/api/groups/${groupId}`),
        request("GET", `/api/groups/${groupId}/balances`),
        request("GET", `/api/groups/${groupId}/activity`),
      ]);

      if (skeletonView.parentNode) {
        main.removeChild(skeletonView);
      }
      // Clear main
      main.replaceChildren();

      renderGroupView(group, balancesData, activity);
    } catch (err) {
      if (skeletonView.parentNode) {
        main.removeChild(skeletonView);
      }
      main.replaceChildren();

      const errMessage = err.status === 403 ? "You're not a member of this group." : (err.message || "Failed to load group.");

      const errState = el(
        "div",
        { className: "card empty-state" },
        el("p", { className: "text-coral", style: { fontSize: "var(--fs-lg)", fontWeight: 600 } }, errMessage),
        el("a", { href: "#/groups", className: "btn btn-primary" }, "Back to groups")
      );
      main.appendChild(errState);
    }
  }

  function renderGroupView(group, balancesData, activity) {
    const members = group.members || [];
    const memberMap = new Map(members.map((m) => [m.id, m]));

    // Top breadcrumb and title bar
    const backLink = el(
      "a",
      {
        href: "#/groups",
        style: {
          display: "inline-flex",
          alignItems: "center",
          gap: "var(--s1)",
          color: "var(--slate)",
          fontWeight: 600,
          fontSize: "var(--fs-sm)",
          marginBottom: "var(--s3)",
          textDecoration: "none",
        },
      },
      "← Groups"
    );

    const groupHeader = el(
      "div",
      {
        style: {
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "var(--s3)",
          paddingBottom: "var(--s4)",
          borderBottom: "1px solid var(--line)",
          marginBottom: "var(--s5)",
        },
      },
      el(
        "div",
        { style: { display: "flex", alignItems: "center", gap: "var(--s4)" } },
        el("h1", { style: { fontSize: "var(--fs-2xl)" } }, group.name),
        avatarStack(members, 32, 5)
      ),
      el(
        "div",
        { style: { display: "flex", alignItems: "center", gap: "var(--s3)" } },
        el(
          "button",
          {
            type: "button",
            className: "btn",
            onClick: () => openMemberDialog(group.id, group.name, () => loadData()),
          },
          "Add member"
        ),
        el(
          "button",
          {
            type: "button",
            className: "btn btn-primary desktop-only",
            onClick: () =>
              openExpenseDialog({
                groupId: group.id,
                members,
                currentUserId: currentUser.id,
                onSaved: () => loadData(),
              }),
          },
          "Add expense"
        )
      )
    );

    // Mobile Fixed Bottom Bar
    const mobileBottomBar = el(
      "div",
      { className: "mobile-bottom-bar" },
      el(
        "button",
        {
          type: "button",
          className: "btn btn-primary",
          onClick: () =>
            openExpenseDialog({
              groupId: group.id,
              members,
              currentUserId: currentUser.id,
              onSaved: () => loadData(),
            }),
        },
        "Add expense"
      )
    );

    // --- Settle-Up Card ---
    const settleCard = el("div", { className: "settle-card", style: { marginBottom: "var(--s5)" } });
    settleCard.appendChild(el("h2", { className: "settle-header" }, "Settle up"));

    const simplified = balancesData.simplified || [];
    if (simplified.length === 0) {
      settleCard.appendChild(
        el(
          "div",
          { style: { display: "flex", alignItems: "center", gap: "var(--s3)", color: "var(--leaf)", padding: "var(--s3) 0" } },
          el(
            "svg",
            { width: 24, height: 24, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2 },
            el("path", { d: "M20 6L9 17l-5-5" })
          ),
          el("span", { style: { fontWeight: 600, fontSize: "var(--fs-md)" } }, "Everyone's settled up.")
        )
      );
    } else {
      // Sort payments: payments involving current user come first!
      const sortedPayments = [...simplified].sort((a, b) => {
        const aInvolves = a.from_user_id === currentUser.id || a.to_user_id === currentUser.id;
        const bInvolves = b.from_user_id === currentUser.id || b.to_user_id === currentUser.id;
        if (aInvolves && !bInvolves) return -1;
        if (!aInvolves && bInvolves) return 1;
        return 0;
      });

      for (const p of sortedPayments) {
        const fromMem = memberMap.get(p.from_user_id) || { id: p.from_user_id, name: "User" };
        const toMem = memberMap.get(p.to_user_id) || { id: p.to_user_id, name: "User" };

        let sentence = "";
        if (p.from_user_id === currentUser.id) {
          sentence = `You pay ${toMem.name}`;
        } else if (p.to_user_id === currentUser.id) {
          sentence = `${fromMem.name} pays You`;
        } else {
          sentence = `${fromMem.name} pays ${toMem.name}`;
        }

        const flow = el(
          "div",
          { className: "settle-flow" },
          avatar(fromMem, 40),
          el(
            "div",
            { className: "settle-connector" },
            el("div", { className: "settle-connector-line" }),
            el("span", { className: "settle-amount-pill" }, formatPaise(p.amount_cents))
          ),
          avatar(toMem, 40)
        );

        const recordBtn = el(
          "button",
          {
            type: "button",
            className: "btn btn-accent btn-sm",
            style: { alignSelf: "flex-end" },
            onClick: () =>
              openPaymentDialog({
                groupId: group.id,
                members,
                currentUserId: currentUser.id,
                fromUserId: p.from_user_id,
                toUserId: p.to_user_id,
                amountCents: p.amount_cents,
                onSettled: () => loadData(),
              }),
          },
          "Record payment"
        );

        const itemEl = el(
          "div",
          { className: "settle-item" },
          flow,
          el(
            "div",
            { style: { display: "flex", justifyContent: "space-between", alignItems: "center" } },
            el("div", { className: "settle-sentence" }, sentence),
            recordBtn
          )
        );
        settleCard.appendChild(itemEl);
      }
    }

    // --- Balances Card ---
    const balancesCard = el("div", { className: "card", style: { marginBottom: "var(--s5)" } });
    balancesCard.appendChild(el("h2", { style: { fontSize: "var(--fs-lg)", marginBottom: "var(--s4)" } }, "Balances"));

    const balances = balancesData.balances || [];
    let maxAbsBalance = 1;
    for (const b of balances) {
      if (Math.abs(b.net_cents) > maxAbsBalance) {
        maxAbsBalance = Math.abs(b.net_cents);
      }
    }

    for (const b of balances) {
      const isMe = b.user_id === currentUser.id;
      const memObj = memberMap.get(b.user_id) || { id: b.user_id, name: b.name };
      const displayName = isMe ? `${b.name} (you)` : b.name;

      let amountText = "₹0";
      let amountClass = "text-slate";
      let ariaLabel = `${displayName} is settled up`;
      let barFillClass = "";
      let barWidthPct = 0;

      if (b.net_cents > 0) {
        amountText = `+${formatPaise(b.net_cents)}`;
        amountClass = "text-leaf";
        ariaLabel = isMe ? `You're owed ${formatPaise(b.net_cents)}` : `${displayName} is owed ${formatPaise(b.net_cents)}`;
        barFillClass = "balance-bar-owed";
        barWidthPct = (b.net_cents / maxAbsBalance) * 50; // max 50% from center
      } else if (b.net_cents < 0) {
        amountText = `−${formatPaise(Math.abs(b.net_cents))}`;
        amountClass = "text-coral";
        ariaLabel = isMe ? `You owe ${formatPaise(Math.abs(b.net_cents))}` : `${displayName} owes ${formatPaise(Math.abs(b.net_cents))}`;
        barFillClass = "balance-bar-owing";
        barWidthPct = (Math.abs(b.net_cents) / maxAbsBalance) * 50;
      }

      const barFill = el("div", {
        className: `balance-bar-fill ${barFillClass}`,
        style: { width: "0%" }, // initial for 600ms orchestrated grow
      });

      const barContainer = el(
        "div",
        {
          className: "balance-bar-container",
          role: "img",
          "aria-label": ariaLabel,
        },
        el("div", { className: "balance-center-line" }),
        barFill
      );

      // Trigger width growth after DOM render
      requestAnimationFrame(() => {
        setTimeout(() => {
          barFill.style.width = `${barWidthPct}%`;
        }, 50);
      });

      const row = el(
        "div",
        { className: "balance-row" },
        avatar(memObj, 32),
        el("span", { className: "balance-name truncate" }, displayName),
        barContainer,
        el("span", { className: `balance-amount ${amountClass}` }, amountText)
      );
      balancesCard.appendChild(row);
    }

    // --- Activity Feed ---
    const activitySection = el("section", { "aria-label": "Activity feed" });
    activitySection.appendChild(el("h2", { style: { fontSize: "var(--fs-xl)", marginBottom: "var(--s4)" } }, "Activity"));

    if (activity.length === 0) {
      activitySection.appendChild(
        el(
          "div",
          { className: "card empty-state" },
          el("p", { className: "empty-state-text" }, "No expenses yet. Add the first one and Halfway will do the maths."),
          el(
            "button",
            {
              type: "button",
              className: "btn btn-primary",
              onClick: () =>
                openExpenseDialog({
                  groupId: group.id,
                  members,
                  currentUserId: currentUser.id,
                  onSaved: () => loadData(),
                }),
            },
            "Add expense"
          )
        )
      );
    } else {
      // Group by Month ("November 2026")
      let currentMonthHeader = "";

      for (const item of activity) {
        const itemMonth = formatMonthYear(item.created_at);
        if (itemMonth !== currentMonthHeader) {
          currentMonthHeader = itemMonth;
          activitySection.appendChild(
            el("h3", { className: "activity-month-header" }, currentMonthHeader)
          );
        }

        if (item.type === "expense" && item.expense) {
          const exp = item.expense;
          const payer = memberMap.get(exp.paid_by) || { name: "Someone" };
          const payerName = exp.paid_by === currentUser.id ? "You" : payer.name;
          const dateStr = formatDate(exp.expense_date);

          // User's position:
          // Lent = paid - own_share when paid_by is current user
          // Owe = own_share when someone else paid
          // Not in this = no share and did not pay
          let posText = "You're not in this";
          let posClass = "text-slate";
          let posAmount = "";

          const mySplit = exp.splits.find((s) => s.user_id === currentUser.id);
          const myShare = mySplit ? mySplit.share_cents : 0;

          if (exp.paid_by === currentUser.id) {
            const lent = exp.amount_cents - myShare;
            if (lent > 0) {
              posText = "You lent";
              posClass = "text-leaf";
              posAmount = formatPaise(lent);
            } else {
              posText = "You paid";
              posClass = "text-slate";
              posAmount = formatPaise(exp.amount_cents);
            }
          } else if (myShare > 0) {
            posText = "You owe";
            posClass = "text-coral";
            posAmount = formatPaise(myShare);
          }

          const card = el(
            "div",
            {
              className: "activity-card",
              onClick: () => openExpenseDetailDialog(exp, group, members, currentUser, () => loadData()),
            },
            el(
              "div",
              { style: { display: "flex", alignItems: "center" } },
              el("div", { className: "activity-icon" }, "🍽"),
              el(
                "div",
                { className: "activity-info" },
                el("div", { className: "activity-desc" }, exp.description),
                el("div", { className: "activity-sub" }, `${payerName} paid ${formatPaise(exp.amount_cents)} · ${dateStr}`)
              )
            ),
            el(
              "div",
              { className: "activity-right" },
              el("div", { className: `activity-user-pos ${posClass}` }, posText),
              posAmount ? el("div", { className: `activity-amount ${posClass}` }, posAmount) : null
            )
          );
          activitySection.appendChild(card);
        } else if (item.type === "settlement" && item.settlement) {
          const st = item.settlement;
          const fromUser = memberMap.get(st.from_user) || { name: "Someone" };
          const toUser = memberMap.get(st.to_user) || { name: "Someone" };

          const fromName = st.from_user === currentUser.id ? "You" : fromUser.name;
          const toName = st.to_user === currentUser.id ? "You" : toUser.name;

          const dateStr = formatDate(st.created_at);
          const noteText = st.note ? ` · ${st.note}` : "";

          const canUndo = currentUser.id === st.created_by || currentUser.id === group.owner_id;

          const undoBtn = canUndo
            ? el(
                "button",
                {
                  type: "button",
                  className: "btn btn-ghost btn-sm",
                  onClick: async (e) => {
                    e.stopPropagation();
                    try {
                      await request("DELETE", `/api/groups/${group.id}/settlements/${st.id}`);
                      toast("Payment undone");
                      loadData();
                    } catch (err) {
                      toast(err.message || "Failed to undo payment", { type: "error" });
                    }
                  },
                },
                "Undo"
              )
            : null;

          const card = el(
            "div",
            { className: "activity-card" },
            el(
              "div",
              { style: { display: "flex", alignItems: "center" } },
              el(
                "div",
                { className: "activity-icon", style: { color: "var(--leaf)" } },
                "✓"
              ),
              el(
                "div",
                { className: "activity-info" },
                el("div", { className: "activity-desc" }, `${fromName} paid ${toName} ${formatPaise(st.amount_cents)}`),
                el("div", { className: "activity-sub" }, `${dateStr}${noteText}`)
              )
            ),
            el("div", { className: "activity-right" }, undoBtn)
          );
          activitySection.appendChild(card);
        }
      }
    }

    // Responsive 2-column container:
    // Desktop: Left (Feed), Right (Sticky Settle-up & Balances)
    // Mobile: Header, Settle-up, Balances, Feed
    const columnsLayout = el(
      "div",
      {
        style: {
          display: "grid",
          gridTemplateColumns: "1fr",
          gap: "var(--s6)",
        },
      }
    );

    const rightColumn = el(
      "div",
      {
        style: {
          display: "flex",
          flexDirection: "column",
        },
      },
      settleCard,
      balancesCard
    );

    // Apply 2-column layout on screens >= 1024px
    const mql = window.matchMedia("(min-width: 1024px)");
    function handleMediaChange(e) {
      if (e.matches) {
        columnsLayout.style.gridTemplateColumns = "1.2fr 0.8fr";
        columnsLayout.replaceChildren(activitySection, rightColumn);
        rightColumn.style.position = "sticky";
        rightColumn.style.top = "80px";
      } else {
        columnsLayout.style.gridTemplateColumns = "1fr";
        columnsLayout.replaceChildren(rightColumn, activitySection);
        rightColumn.style.position = "static";
      }
    }
    mql.addEventListener("change", handleMediaChange);
    handleMediaChange(mql);

    main.appendChild(backLink);
    main.appendChild(groupHeader);
    main.appendChild(columnsLayout);
    main.appendChild(mobileBottomBar);
  }

  loadData();
}

/**
 * Open detail dialog for an expense.
 */
function openExpenseDetailDialog(expense, group, members, currentUser, onModified) {
  const memberMap = new Map(members.map((m) => [m.id, m]));
  const payer = memberMap.get(expense.paid_by) || { name: "Someone" };
  const creator = memberMap.get(expense.created_by) || { name: "Someone" };

  const canEditOrDelete =
    currentUser.id === expense.created_by || currentUser.id === group.owner_id;

  let closeDialogFn;

  const splitsList = el("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: "var(--s2)",
      margin: "var(--s4) 0",
      borderTop: "1px solid var(--line)",
      borderBottom: "1px solid var(--line)",
      padding: "var(--s3) 0",
    },
  });

  for (const s of expense.splits) {
    const mem = memberMap.get(s.user_id) || { name: "Someone" };
    const row = el(
      "div",
      { style: { display: "flex", justifyContent: "space-between", alignItems: "center" } },
      el(
        "div",
        { style: { display: "flex", alignItems: "center", gap: "var(--s2)" } },
        avatar(mem, 24),
        el("span", {}, mem.name + (s.user_id === currentUser.id ? " (you)" : ""))
      ),
      el("span", { className: "money", style: { fontWeight: 600 } }, formatPaise(s.share_cents))
    );
    splitsList.appendChild(row);
  }

  const actions = el("div", { className: "dialog-actions" });

  if (canEditOrDelete) {
    const deleteBtn = el(
      "button",
      {
        type: "button",
        className: "btn btn-danger",
        onClick: async () => {
          closeDialogFn();
          const confirmed = await confirmDialog({
            title: "Delete this expense?",
            body: `${expense.description}, ${formatPaise(expense.amount_cents)}. Balances will update right away.`,
            confirmLabel: "Delete expense",
          });
          if (confirmed) {
            try {
              await request("DELETE", `/api/groups/${group.id}/expenses/${expense.id}`);
              toast("Expense deleted");
              onModified();
            } catch (err) {
              toast(err.message || "Failed to delete expense", { type: "error" });
            }
          }
        },
      },
      "Delete"
    );

    const editBtn = el(
      "button",
      {
        type: "button",
        className: "btn btn-primary",
        onClick: () => {
          closeDialogFn();
          openExpenseDialog({
            groupId: group.id,
            members,
            currentUserId: currentUser.id,
            expense,
            onSaved: onModified,
          });
        },
      },
      "Edit"
    );

    actions.appendChild(deleteBtn);
    actions.appendChild(editBtn);
  }

  const content = el(
    "div",
    {},
    el(
      "div",
      { style: { marginBottom: "var(--s3)" } },
      el("div", { className: "money font-display", style: { fontSize: "var(--fs-2xl)", fontWeight: 700, color: "var(--ink)" } }, formatPaise(expense.amount_cents)),
      el("div", { style: { color: "var(--slate)", fontSize: "var(--fs-sm)", marginTop: "var(--s1)" } }, `Paid by ${payer.name} on ${formatDate(expense.expense_date)} · Added by ${creator.name}`)
    ),
    el("div", { style: { fontWeight: 600, fontSize: "var(--fs-sm)", color: "var(--slate)" } }, `Split ${expense.split_type}:`),
    splitsList,
    actions
  );

  closeDialogFn = openDialog(content, { title: expense.description });
}
