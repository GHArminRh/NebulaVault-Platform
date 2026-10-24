(() => {
  "use strict";

  const endpoint = "/admin/quick-toggle/";
  const protectedFields = new Set(["is_staff", "is_superuser"]);

  function csrfToken() {
    const entry = document.cookie.split("; ").find((part) => part.startsWith("csrftoken="));
    return entry ? decodeURIComponent(entry.split("=").slice(1).join("=")) : "";
  }

  function objectIdForRow(row) {
    if (row.dataset.objectPk) return row.dataset.objectPk;
    const action = row.querySelector('input[name="_selected_action"]');
    if (action) return action.value;
    const changeLink = row.querySelector('th a[href$="/change/"], td a[href$="/change/"]');
    if (changeLink) {
      const match = changeLink.getAttribute("href").match(/\/([^/]+)\/change\/$/);
      if (match) return decodeURIComponent(match[1]);
    }
    return null;
  }

  function appAndModel() {
    const parts = window.location.pathname.split("/").filter(Boolean);
    const adminIndex = parts.indexOf("admin");
    if (adminIndex < 0 || !parts[adminIndex + 1] || !parts[adminIndex + 2]) return null;
    return { app_label: parts[adminIndex + 1], model_name: parts[adminIndex + 2] };
  }

  function renderButton(cell, currentValue, context) {
    if (cell.querySelector(".nv-boolean-toggle")) return;
    const fieldClass = Array.from(cell.classList).find((name) => name.startsWith("field-"));
    if (!fieldClass) return;
    const fieldName = fieldClass.slice("field-".length);
    if (!fieldName || protectedFields.has(fieldName)) return;

    const button = document.createElement("button");
    button.type = "button";
    button.className = "nv-boolean-toggle " + (currentValue ? "is-true" : "is-false");
    button.textContent = currentValue ? "✓" : "✕";
    button.setAttribute("aria-label", (currentValue ? "Enabled" : "Disabled") + "; click to toggle");
    button.title = "Click to " + (currentValue ? "disable" : "enable");
    button.dataset.value = String(currentValue);
    button.addEventListener("click", async () => {
      if (button.disabled) return;
      const nextValue = button.dataset.value !== "true";
      button.disabled = true;
      button.classList.add("is-saving");
      try {
        const response = await fetch(endpoint, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken(),
            "X-Requested-With": "XMLHttpRequest"
          },
          body: JSON.stringify({
            ...context,
            object_id: objectIdForRow(cell.closest("tr")),
            field_name: fieldName,
            value: nextValue
          })
        });
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || "Could not save this change.");
        button.dataset.value = String(data.value);
        button.textContent = data.value ? "✓" : "✕";
        button.classList.toggle("is-true", data.value);
        button.classList.toggle("is-false", !data.value);
        button.setAttribute("aria-label", (data.value ? "Enabled" : "Disabled") + "; click to toggle");
        button.title = "Click to " + (data.value ? "disable" : "enable");
      } catch (error) {
        window.alert(error.message || "Could not save this change.");
      } finally {
        button.disabled = false;
        button.classList.remove("is-saving");
      }
    });
    cell.replaceChildren(button);
  }

  function enhanceBooleanCells() {
    const context = appAndModel();
    if (!context) return;
    document.querySelectorAll("#result_list tbody tr").forEach((row) => {
      const cells = row.querySelectorAll("td[class*='field-']");
      cells.forEach((cell) => {
        const icon = cell.querySelector('img[alt="True"], img[alt="False"]');
        if (!icon) return;
        renderButton(cell, icon.alt === "True", context);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enhanceBooleanCells);
  } else {
    enhanceBooleanCells();
  }
})();
