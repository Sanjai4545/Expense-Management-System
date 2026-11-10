import { el, openDialog, toast } from "../ui.js";
import { request, ApiError } from "../api.js";

/**
 * Open dialog to add a new member by email.
 */
export function openMemberDialog(groupId, groupName, onMemberAdded) {
  let isSubmitting = false;

  const emailInput = el("input", {
    type: "email",
    className: "input",
    id: "member-email",
    placeholder: "friend@example.com",
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
    "Add member"
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
        emailInput.classList.remove("is-error");

        const email = emailInput.value.trim();
        if (!email) return;

        isSubmitting = true;
        submitBtn.disabled = true;
        submitBtn.textContent = "Adding…";

        try {
          const newMember = await request("POST", `/api/groups/${groupId}/members`, { email });
          toast(`${newMember.name} joined ${groupName}`);
          closeDialogFn();
          if (onMemberAdded) {
            onMemberAdded(newMember);
          }
        } catch (err) {
          isSubmitting = false;
          submitBtn.disabled = false;
          submitBtn.textContent = "Add member";

          emailInput.classList.add("is-error");
          errorMsg.textContent = err.message || "Failed to add member.";
          errorMsg.style.display = "flex";
        }
      },
    },
    el(
      "div",
      { className: "form-group" },
      el("label", { className: "form-label", htmlFor: "member-email" }, "Friend's email address"),
      emailInput,
      errorMsg
    ),
    el(
      "div",
      { className: "dialog-actions" },
      submitBtn
    )
  );

  closeDialogFn = openDialog(form, {
    title: "Add member",
    onUnsavedCheck: () => emailInput.value.trim().length > 0,
  });

  setTimeout(() => emailInput.focus(), 50);
}
