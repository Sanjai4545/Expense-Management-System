import { el, openDialog, toast } from "../ui.js";
import { formatPaise, parseRupeesToPaise, parsePercentToBasisPoints, formatBasisPoints } from "../money.js";
import { request, ApiError } from "../api.js";

/**
 * JS equivalent of core split_equal algorithm for live preview.
 */
function splitEqualPreview(amountPaise, userIds) {
  if (!userIds || userIds.length === 0 || !amountPaise) return {};
  const sorted = [...userIds].sort((a, b) => a - b);
  const n = sorted.length;
  const base = Math.floor(amountPaise / n);
  const rem = amountPaise % n;
  const res = {};
  for (let i = 0; i < sorted.length; i++) {
    res[sorted[i]] = base + (i < rem ? 1 : 0);
  }
  return res;
}

export function openExpenseDialog({
  groupId,
  members,
  currentUserId,
  expense = null, // if provided, edit mode
  onSaved,
}) {
  const isEdit = !!expense;
  let isSubmitting = false;

  // Form field elements
  const descInput = el("input", {
    type: "text",
    className: "input",
    id: "exp-desc",
    placeholder: "e.g. Dinner at Fisherman's Wharf",
    value: expense ? expense.description : "",
    required: true,
    maxLength: 100,
  });
  const descError = el("div", { className: "input-error-msg", style: { display: "none" } });

  const amountInput = el("input", {
    type: "text",
    className: "input input-money",
    id: "exp-amount",
    inputmode: "decimal",
    autocomplete: "off",
    placeholder: "0",
    value: expense ? (expense.amount_cents / 100).toString() : "",
    required: true,
  });
  const amountError = el("div", { className: "input-error-msg", style: { display: "none" } });

  const paidBySelect = el("select", { className: "select", id: "exp-paid-by" });
  for (const m of members) {
    const opt = el("option", { value: m.id }, m.name + (m.id === currentUserId ? " (you)" : ""));
    if (expense ? m.id === expense.paid_by : m.id === currentUserId) {
      opt.selected = true;
    }
    paidBySelect.appendChild(opt);
  }

  // Today UTC date string: YYYY-MM-DD
  const todayUtc = new Date().toISOString().slice(0, 10);
  const dateInput = el("input", {
    type: "date",
    className: "input",
    id: "exp-date",
    value: expense ? expense.expense_date : todayUtc,
    required: true,
  });
  const dateError = el("div", { className: "input-error-msg", style: { display: "none" } });

  // Split Type: Equal, Exact, Percent
  let splitType = expense ? expense.split_type : "equal";

  const radioEqual = el("input", { type: "radio", name: "split_type", id: "st-equal", value: "equal" });
  const radioExact = el("input", { type: "radio", name: "split_type", id: "st-exact", value: "exact" });
  const radioPercent = el("input", { type: "radio", name: "split_type", id: "st-percent", value: "percent" });

  if (splitType === "equal") radioEqual.checked = true;
  if (splitType === "exact") radioExact.checked = true;
  if (splitType === "percent") radioPercent.checked = true;

  const splitControl = el(
    "div",
    { className: "segmented-control", role: "radiogroup", "aria-label": "Split type" },
    el("div", { className: "segmented-option" }, radioEqual, el("label", { htmlFor: "st-equal", className: "segmented-label" }, "Equally")),
    el("div", { className: "segmented-option" }, radioExact, el("label", { htmlFor: "st-exact", className: "segmented-label" }, "Exact amounts")),
    el("div", { className: "segmented-option" }, radioPercent, el("label", { htmlFor: "st-percent", className: "segmented-label" }, "Percentages"))
  );

  // Dynamic people list section
  const peopleContainer = el("div", { style: { marginTop: "var(--s4)" } });
  const statusLine = el("div", {
    className: "money",
    style: { fontSize: "var(--fs-sm)", fontWeight: 600, marginTop: "var(--s2)", minHeight: "20px" },
  });
  const generalError = el("div", { className: "input-error-msg", style: { display: "none", marginBottom: "var(--s3)" } });

  const submitBtn = el(
    "button",
    {
      type: "submit",
      className: "btn btn-primary",
    },
    isEdit ? "Save changes" : "Add expense"
  );

  // Participant state tracking
  // Equal: Set of checked user IDs
  const checkedEqual = new Set(
    expense && expense.split_type === "equal"
      ? expense.splits.map((s) => s.user_id)
      : members.map((m) => m.id)
  );

  // Exact: Map of userId -> input string
  const exactInputs = new Map();
  if (expense && expense.split_type === "exact") {
    for (const s of expense.splits) {
      exactInputs.set(s.user_id, (s.share_cents / 100).toString());
    }
  }

  // Percent: Map of userId -> input string
  const percentInputs = new Map();
  if (expense && expense.split_type === "percent") {
    // basis points to percentage display
    for (const s of expense.splits) {
      percentInputs.set(s.user_id, (s.share_cents / 100).toString()); // share_cents stores basis points or shares
    }
  }

  function renderPeopleList() {
    peopleContainer.replaceChildren();
    statusLine.textContent = "";
    submitBtn.disabled = false;

    const parsedAmount = parseRupeesToPaise(amountInput.value) || 0;

    if (splitType === "equal") {
      // "Select all / none" toggle
      const allSelected = checkedEqual.size === members.length;
      const toggleAllBtn = el(
        "button",
        {
          type: "button",
          className: "btn btn-ghost btn-sm",
          style: { alignSelf: "flex-end", marginBottom: "var(--s2)" },
          onClick: () => {
            if (allSelected) {
              checkedEqual.clear();
            } else {
              members.forEach((m) => checkedEqual.add(m.id));
            }
            renderPeopleList();
          },
        },
        allSelected ? "Deselect all" : "Select all"
      );

      const headerRow = el(
        "div",
        { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--s2)" } },
        el("span", { style: { fontSize: "var(--fs-sm)", fontWeight: 600 } }, "Split equally between:"),
        toggleAllBtn
      );
      peopleContainer.appendChild(headerRow);

      const previewShares = splitEqualPreview(parsedAmount, Array.from(checkedEqual));

      const listEl = el("div", { style: { display: "flex", flexDirection: "column", gap: "var(--s2)" } });
      for (const m of members) {
        const isChecked = checkedEqual.has(m.id);
        const shareVal = previewShares[m.id];
        const shareText = isChecked && parsedAmount > 0 && shareVal !== undefined ? formatPaise(shareVal) : "₹0";

        const cb = el("input", {
          type: "checkbox",
          id: `eq-mem-${m.id}`,
          checked: isChecked,
          onChange: (e) => {
            if (e.target.checked) {
              checkedEqual.add(m.id);
            } else {
              checkedEqual.delete(m.id);
            }
            renderPeopleList();
          },
        });

        const row = el(
          "label",
          {
            htmlFor: `eq-mem-${m.id}`,
            style: {
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "var(--s2) var(--s3)",
              background: isChecked ? "var(--lagoon-wash)" : "var(--paper)",
              border: "1px solid var(--line)",
              borderRadius: "var(--r-control)",
              cursor: "pointer",
            },
          },
          el(
            "div",
            { style: { display: "flex", alignItems: "center", gap: "var(--s2)" } },
            cb,
            el("span", { style: { fontWeight: 500 } }, m.name + (m.id === currentUserId ? " (you)" : ""))
          ),
          el("span", { className: "money", style: { fontWeight: 600, color: isChecked ? "var(--lagoon)" : "var(--slate)" } }, shareText)
        );
        listEl.appendChild(row);
      }
      peopleContainer.appendChild(listEl);

      if (checkedEqual.size === 0) {
        submitBtn.disabled = true;
        statusLine.textContent = "Select at least one person.";
        statusLine.style.color = "var(--coral)";
      }
    } else if (splitType === "exact") {
      let currentTotalPaise = 0;
      const listEl = el("div", { style: { display: "flex", flexDirection: "column", gap: "var(--s3)" } });

      for (const m of members) {
        const currentVal = exactInputs.get(m.id) || "";
        const rowAmount = parseRupeesToPaise(currentVal) || 0;
        currentTotalPaise += rowAmount;

        const rowInput = el("input", {
          type: "text",
          className: "input input-money",
          style: { height: "40px", maxWidth: "140px" },
          placeholder: "0",
          value: currentVal,
          onInput: (e) => {
            exactInputs.set(m.id, e.target.value);
            updateExactStatus();
          },
        });

        const row = el(
          "div",
          {
            style: {
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "var(--s2) var(--s3)",
              border: "1px solid var(--line)",
              borderRadius: "var(--r-control)",
            },
          },
          el("span", { style: { fontWeight: 500 } }, m.name + (m.id === currentUserId ? " (you)" : "")),
          el(
            "div",
            { className: "money-input-wrapper" },
            el("span", { className: "money-currency-symbol", style: { left: "8px" } }, "₹"),
            rowInput
          )
        );
        listEl.appendChild(row);
      }
      peopleContainer.appendChild(listEl);

      function updateExactStatus() {
        let sum = 0;
        for (const m of members) {
          sum += parseRupeesToPaise(exactInputs.get(m.id) || "") || 0;
        }
        const diff = parsedAmount - sum;
        if (parsedAmount === 0) {
          statusLine.textContent = "Enter total amount first.";
          statusLine.style.color = "var(--slate)";
          submitBtn.disabled = true;
        } else if (diff === 0) {
          statusLine.textContent = "All assigned";
          statusLine.style.color = "var(--leaf)";
          submitBtn.disabled = false;
        } else if (diff > 0) {
          statusLine.textContent = `${formatPaise(diff)} left to assign`;
          statusLine.style.color = "var(--slate)";
          submitBtn.disabled = true;
        } else {
          statusLine.textContent = `${formatPaise(Math.abs(diff))} over`;
          statusLine.style.color = "var(--coral)";
          submitBtn.disabled = true;
        }
      }
      updateExactStatus();
    } else if (splitType === "percent") {
      const headerRow = el(
        "div",
        { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--s2)" } },
        el("span", { style: { fontSize: "var(--fs-sm)", fontWeight: 600 } }, "Enter percentage per member:"),
        el(
          "button",
          {
            type: "button",
            className: "btn btn-ghost btn-sm",
            onClick: () => {
              // "Split evenly" helper button fills equal percentages (last person absorbs rounding so sum is 10000 bps)
              const n = members.length;
              const baseBp = Math.floor(10000 / n);
              const rem = 10000 % n;
              members.forEach((m, idx) => {
                const bp = baseBp + (idx === n - 1 ? rem : 0);
                const pctStr = (bp / 100).toFixed(2).replace(/\.00$/, "");
                percentInputs.set(m.id, pctStr);
              });
              renderPeopleList();
            },
          },
          "Split evenly"
        )
      );
      peopleContainer.appendChild(headerRow);

      const listEl = el("div", { style: { display: "flex", flexDirection: "column", gap: "var(--s3)" } });
      for (const m of members) {
        const currentVal = percentInputs.get(m.id) || "";
        const rowInput = el("input", {
          type: "text",
          className: "input",
          style: { height: "40px", maxWidth: "120px", textAlign: "right" },
          placeholder: "0%",
          value: currentVal ? `${currentVal}%` : "",
          onFocus: (e) => {
            // Remove % on focus
            e.target.value = percentInputs.get(m.id) || "";
          },
          onBlur: (e) => {
            const v = e.target.value.trim().replace(/%/g, "");
            if (v) e.target.value = `${v}%`;
          },
          onInput: (e) => {
            percentInputs.set(m.id, e.target.value.replace(/%/g, ""));
            updatePercentStatus();
          },
        });

        const row = el(
          "div",
          {
            style: {
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "var(--s2) var(--s3)",
              border: "1px solid var(--line)",
              borderRadius: "var(--r-control)",
            },
          },
          el("span", { style: { fontWeight: 500 } }, m.name + (m.id === currentUserId ? " (you)" : "")),
          rowInput
        );
        listEl.appendChild(row);
      }
      peopleContainer.appendChild(listEl);

      function updatePercentStatus() {
        let sumBps = 0;
        for (const m of members) {
          sumBps += parsePercentToBasisPoints(percentInputs.get(m.id) || "") || 0;
        }
        const diff = 10000 - sumBps;
        if (diff === 0) {
          statusLine.textContent = "100% assigned";
          statusLine.style.color = "var(--leaf)";
          submitBtn.disabled = false;
        } else if (diff > 0) {
          statusLine.textContent = `${formatBasisPoints(diff)} left`;
          statusLine.style.color = "var(--slate)";
          submitBtn.disabled = true;
        } else {
          statusLine.textContent = `${formatBasisPoints(Math.abs(diff))} over`;
          statusLine.style.color = "var(--coral)";
          submitBtn.disabled = true;
        }
      }
      updatePercentStatus();
    }
  }

  // Radio split type change listeners
  radioEqual.addEventListener("change", () => {
    splitType = "equal";
    renderPeopleList();
  });
  radioExact.addEventListener("change", () => {
    splitType = "exact";
    renderPeopleList();
  });
  radioPercent.addEventListener("change", () => {
    splitType = "percent";
    renderPeopleList();
  });

  amountInput.addEventListener("input", () => {
    renderPeopleList();
  });

  renderPeopleList();

  let closeDialogFn;

  const form = el(
    "form",
    {
      onSubmit: async (e) => {
        e.preventDefault();
        if (isSubmitting) return;

        // Clear error states
        descError.style.display = "none";
        descInput.classList.remove("is-error");
        amountError.style.display = "none";
        amountInput.classList.remove("is-error");
        generalError.style.display = "none";

        const description = descInput.value.trim();
        if (!description) {
          descError.textContent = "Enter a description.";
          descError.style.display = "flex";
          descInput.classList.add("is-error");
          descInput.focus();
          return;
        }

        const amountCents = parseRupeesToPaise(amountInput.value);
        if (!amountCents) {
          amountError.textContent = "Enter an amount like 250 or 250.50.";
          amountError.style.display = "flex";
          amountInput.classList.add("is-error");
          amountInput.focus();
          return;
        }

        const paidBy = parseInt(paidBySelect.value, 10);
        const expDate = dateInput.value;

        // Build participants list according to splitType
        const participants = [];
        if (splitType === "equal") {
          if (checkedEqual.size === 0) {
            generalError.textContent = "Select at least one participant.";
            generalError.style.display = "flex";
            return;
          }
          for (const uid of checkedEqual) {
            participants.push({ user_id: uid, value: null });
          }
        } else if (splitType === "exact") {
          let sum = 0;
          for (const m of members) {
            const val = parseRupeesToPaise(exactInputs.get(m.id) || "") || 0;
            if (val > 0) {
              participants.push({ user_id: m.id, value: val });
              sum += val;
            }
          }
          if (sum !== amountCents) {
            generalError.textContent = `The amounts add up to ${formatPaise(sum)} but the total is ${formatPaise(amountCents)}.`;
            generalError.style.display = "flex";
            return;
          }
        } else if (splitType === "percent") {
          let sumBps = 0;
          for (const m of members) {
            const bp = parsePercentToBasisPoints(percentInputs.get(m.id) || "") || 0;
            if (bp > 0) {
              participants.push({ user_id: m.id, value: bp });
              sumBps += bp;
            }
          }
          if (sumBps !== 10000) {
            generalError.textContent = "The percentages must add up to 100%.";
            generalError.style.display = "flex";
            return;
          }
        }

        isSubmitting = true;
        submitBtn.disabled = true;
        submitBtn.textContent = isEdit ? "Saving…" : "Adding…";

        const payload = {
          description,
          amount_cents: amountCents,
          paid_by: paidBy,
          split_type: splitType,
          expense_date: expDate,
          participants,
        };

        try {
          if (isEdit) {
            await request("PUT", `/api/groups/${groupId}/expenses/${expense.id}`, payload);
            toast("Expense updated");
          } else {
            await request("POST", `/api/groups/${groupId}/expenses`, payload);
            toast("Expense added");
          }
          closeDialogFn();
          if (onSaved) onSaved();
        } catch (err) {
          isSubmitting = false;
          submitBtn.disabled = false;
          submitBtn.textContent = isEdit ? "Save changes" : "Add expense";

          if (err instanceof ApiError && err.fields) {
            if (err.fields.description) {
              descError.textContent = err.fields.description;
              descError.style.display = "flex";
              descInput.classList.add("is-error");
            }
            if (err.fields.amount_cents) {
              amountError.textContent = err.fields.amount_cents;
              amountError.style.display = "flex";
              amountInput.classList.add("is-error");
            }
          } else {
            generalError.textContent = err.message || "Failed to save expense.";
            generalError.style.display = "flex";
          }
        }
      },
    },
    el(
      "div",
      { className: "form-group" },
      el("label", { className: "form-label", htmlFor: "exp-desc" }, "Description"),
      descInput,
      descError
    ),
    el(
      "div",
      { className: "form-group" },
      el("label", { className: "form-label", htmlFor: "exp-amount" }, "Amount"),
      el(
        "div",
        { className: "money-input-wrapper" },
        el("span", { className: "money-currency-symbol" }, "₹"),
        amountInput
      ),
      amountError
    ),
    el(
      "div",
      { className: "form-group" },
      el("label", { className: "form-label", htmlFor: "exp-paid-by" }, "Paid by"),
      paidBySelect
    ),
    el(
      "div",
      { className: "form-group" },
      el("label", { className: "form-label", htmlFor: "exp-date" }, "Date"),
      dateInput,
      dateError
    ),
    el(
      "div",
      { className: "form-group" },
      el("label", { className: "form-label" }, "Split"),
      splitControl
    ),
    peopleContainer,
    statusLine,
    generalError,
    el("div", { className: "dialog-actions" }, submitBtn)
  );

  closeDialogFn = openDialog(form, {
    title: isEdit ? "Edit expense" : "Add expense",
    onUnsavedCheck: () => descInput.value.trim().length > 0 || amountInput.value.trim().length > 0,
  });

  setTimeout(() => descInput.focus(), 50);
}
