import { el, openDialog, toast } from "../ui.js";
import { formatPaise, parseRupeesToPaise } from "../money.js";
import { request, ApiError } from "../api.js";

/**
 * Open dialog to record a payment/settlement.
 */
export function openPaymentDialog({
  groupId,
  members,
  currentUserId,
  fromUserId = null,
  toUserId = null,
  amountCents = null,
  onSettled,
}) {
  let isSubmitting = false;

  // Defaults: fromUser and toUser
  let defaultFrom = fromUserId || currentUserId;
  let defaultTo = toUserId;
  if (!defaultTo) {
    const otherMember = members.find((m) => m.id !== defaultFrom);
    defaultTo = otherMember ? otherMember.id : defaultFrom;
  }

  const fromSelect = el("select", { className: "select", id: "pay-from" });
  const toSelect = el("select", { className: "select", id: "pay-to" });

  function populateSelects() {
    fromSelect.replaceChildren();
    toSelect.replaceChildren();

    const selectedFrom = parseInt(fromSelect.value, 10) || defaultFrom;
    const selectedTo = parseInt(toSelect.value, 10) || defaultTo;

    for (const m of members) {
      const optFrom = el("option", { value: m.id }, m.name + (m.id === currentUserId ? " (you)" : ""));
      if (m.id === selectedFrom) optFrom.selected = true;
      fromSelect.appendChild(optFrom);

      const optTo = el("option", { value: m.id }, m.name + (m.id === currentUserId ? " (you)" : ""));
      if (m.id === selectedTo) optTo.selected = true;
      if (m.id === selectedFrom) optTo.disabled = true; // disable chosen payer
      toSelect.appendChild(optTo);
    }
  }

  populateSelects();

  fromSelect.addEventListener("change", () => {
    populateSelects();
    // If toSelect now equals fromSelect, pick another
    if (fromSelect.value === toSelect.value) {
      const other = members.find((m) => String(m.id) !== fromSelect.value);
      if (other) toSelect.value = String(other.id);
    }
    populateSelects();
  });

  const amountInput = el("input", {
    type: "text",
    className: "input input-money",
    id: "pay-amount",
    inputmode: "decimal",
    autocomplete: "off",
    placeholder: "0",
    value: amountCents ? (amountCents / 100).toString() : "",
    required: true,
  });
  const amountError = el("div", { className: "input-error-msg", style: { display: "none" } });

  const noteInput = el("input", {
    type: "text",
    className: "input",
    id: "pay-note",
    placeholder: "e.g. UPI, cash, bank transfer (optional)",
    maxLength: 100,
  });

  const generalError = el("div", { className: "input-error-msg", style: { display: "none", marginBottom: "var(--s3)" } });

  const submitBtn = el(
    "button",
    {
      type: "submit",
      className: "btn btn-accent",
    },
    "Record payment"
  );

  let closeDialogFn;

  const form = el(
    "form",
    {
      onSubmit: async (e) => {
        e.preventDefault();
        if (isSubmitting) return;

        amountError.style.display = "none";
        amountInput.classList.remove("is-error");
        generalError.style.display = "none";

        const parsedAmount = parseRupeesToPaise(amountInput.value);
        if (!parsedAmount) {
          amountError.textContent = "Enter an amount like 250 or 250.50.";
          amountError.style.display = "flex";
          amountInput.classList.add("is-error");
          amountInput.focus();
          return;
        }

        const fromVal = parseInt(fromSelect.value, 10);
        const toVal = parseInt(toSelect.value, 10);

        if (fromVal === toVal) {
          generalError.textContent = "You can't pay yourself.";
          generalError.style.display = "flex";
          return;
        }

        isSubmitting = true;
        submitBtn.disabled = true;
        submitBtn.textContent = "Recording…";

        const payload = {
          from_user: fromVal,
          to_user: toVal,
          amount_cents: parsedAmount,
          note: noteInput.value.trim() || null,
        };

        try {
          const settlement = await request("POST", `/api/groups/${groupId}/settlements`, payload);
          closeDialogFn();

          toast("Payment recorded", {
            action: {
              label: "Undo",
              onClick: async () => {
                try {
                  await request("DELETE", `/api/groups/${groupId}/settlements/${settlement.id}`);
                  toast("Payment undone");
                  if (onSettled) onSettled();
                } catch (undoErr) {
                  toast(undoErr.message || "Failed to undo payment", { type: "error" });
                }
              },
            },
          });

          if (onSettled) onSettled();
        } catch (err) {
          isSubmitting = false;
          submitBtn.disabled = false;
          submitBtn.textContent = "Record payment";

          if (err instanceof ApiError && err.fields && err.fields.amount_cents) {
            amountError.textContent = err.fields.amount_cents;
            amountError.style.display = "flex";
            amountInput.classList.add("is-error");
          } else {
            generalError.textContent = err.message || "Failed to record payment.";
            generalError.style.display = "flex";
          }
        }
      },
    },
    el(
      "div",
      { className: "form-group" },
      el("label", { className: "form-label", htmlFor: "pay-from" }, "Who paid"),
      fromSelect
    ),
    el(
      "div",
      { className: "form-group" },
      el("label", { className: "form-label", htmlFor: "pay-to" }, "Who received"),
      toSelect
    ),
    el(
      "div",
      { className: "form-group" },
      el("label", { className: "form-label", htmlFor: "pay-amount" }, "Amount"),
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
      el("label", { className: "form-label", htmlFor: "pay-note" }, "Note (optional)"),
      noteInput
    ),
    generalError,
    el("div", { className: "dialog-actions" }, submitBtn)
  );

  closeDialogFn = openDialog(form, {
    title: "Record payment",
    onUnsavedCheck: () => amountInput.value.trim().length > 0 || noteInput.value.trim().length > 0,
  });

  setTimeout(() => amountInput.focus(), 50);
}
