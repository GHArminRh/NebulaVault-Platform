(() => {
  "use strict";

  const endpoint = "/admin/quick-toggle/";
  const protectedFields = new Set(["is_staff", "is_superuser"]);
  const actionCellClass = "nv-record-actions";
  const iconStyle = "width:10px;height:10px;display:inline-block;vertical-align:middle;border:0;";


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

  function renderButton(cell, icon, context) {
    const currentValue = icon.alt === "True";
    if (cell.querySelector(".nv-boolean-toggle")) return;
    const fieldClass = Array.from(cell.classList).find((name) => name.startsWith("field-"));
    if (!fieldClass) return;
    const fieldName = fieldClass.slice("field-".length);
    if (!fieldName || protectedFields.has(fieldName)) return;

    // Keep Django's original status image, including its native src, alt and classes.
    const button = document.createElement("button");
    button.type = "button";
    button.className = "nv-boolean-toggle";
    button.style.appearance = "none";
    button.style.webkitAppearance = "none";
    button.style.border = "0";
    button.style.background = "transparent";
    button.style.padding = "0";
    button.style.margin = "0";
    button.style.font = "inherit";
    button.style.lineHeight = "inherit";
    button.style.color = "inherit";
    button.style.cursor = "pointer";
    button.style.verticalAlign = "middle";
    button.appendChild(icon);
    button.setAttribute("aria-label", (currentValue ? "Enabled" : "Disabled") + "; click to toggle");
    button.title = "Click to " + (currentValue ? "disable" : "enable");
    button.dataset.value = String(currentValue);

    button.addEventListener("click", async () => {
      if (button.disabled) return;
      const nextValue = button.dataset.value !== "true";
      button.disabled = true;
      button.style.cursor = "wait";
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

        const next = Boolean(data.value);
        button.dataset.value = String(next);
        // Swap only the filename; preserve Django's native icon asset and styling.
        const url = new URL(icon.getAttribute("src"), window.location.href);
        url.pathname = url.pathname.replace(/icon-(yes|no)\.svg$/, next ? "icon-yes.svg" : "icon-no.svg");
        icon.setAttribute("src", url.pathname + url.search + url.hash);
        icon.alt = next ? "True" : "False";
        button.setAttribute("aria-label", (next ? "Enabled" : "Disabled") + "; click to toggle");
        button.title = "Click to " + (next ? "disable" : "enable");
      } catch (error) {
        window.alert(error.message || "Could not save this change.");
      } finally {
        button.disabled = false;
        button.style.cursor = "pointer";
      }
    });
    cell.replaceChildren(button);
  }

  function addRecordActions(row, context) {
    if (row.querySelector("." + actionCellClass)) return;
    const objectId = objectIdForRow(row);
    if (!objectId) return;

    const cell = document.createElement("td");
    cell.className = actionCellClass;
    cell.style.whiteSpace = "nowrap";
    cell.style.textAlign = "center";
    cell.style.verticalAlign = "middle";

    const deleteLink = document.createElement("a");
    deleteLink.href = "/admin/" + encodeURIComponent(context.app_label) + "/" +
      encodeURIComponent(context.model_name) + "/" + encodeURIComponent(objectId) + "/delete/";
    deleteLink.className = "nv-record-action nv-record-delete";
    deleteLink.title = "Delete this record";
    deleteLink.setAttribute("aria-label", "Delete this record");
    deleteLink.style.cssText = "display:inline-block;margin:0 4px;line-height:1;";
    const deleteIcon = document.createElement("img");
    deleteIcon.src = "/static/admin/img/icon-deletelink.svg";
    deleteIcon.alt = "";
    deleteIcon.style.cssText = iconStyle;
    deleteLink.appendChild(deleteIcon);

    const exportLink = document.createElement("a");
    exportLink.href = "/admin/json-export/" + encodeURIComponent(context.app_label) + "/" +
      encodeURIComponent(context.model_name) + "/" + encodeURIComponent(objectId) + "/";
    exportLink.className = "nv-record-action nv-record-export";
    exportLink.title = "Export this record as JSON";
    exportLink.setAttribute("aria-label", "Export this record as JSON");
    exportLink.style.cssText = "display:inline-block;margin:0 4px;line-height:1;";
    const exportIcon = document.createElement("img");
    exportIcon.src = "/static/portal/img/icon-json-export.svg";
    exportIcon.alt = "";
    exportIcon.style.cssText = iconStyle;
    exportLink.appendChild(exportIcon);

    cell.append(deleteLink, exportLink);
    row.appendChild(cell);
  }

  function addActionsHeader() {
    const table = document.querySelector("#result_list");
    const headerRow = table && table.querySelector("thead tr");
    if (!headerRow || headerRow.querySelector("." + actionCellClass + "-header")) return;
    const header = document.createElement("th");
    header.className = actionCellClass + "-header";
    header.scope = "col";
    header.textContent = "Tools";
    header.style.textAlign = "center";
    headerRow.appendChild(header);
  }

  function addImportLink(context) {
    const objectTools = document.querySelector(".object-tools");
    if (!objectTools || objectTools.querySelector(".nv-json-import-link")) return;
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = "/admin/json-import/" + encodeURIComponent(context.app_label) + "/" +
      encodeURIComponent(context.model_name) + "/";
    link.className = "nv-json-import-link";
    link.textContent = "Import JSON";
    link.title = "Import one or more JSON exports for this model";
    item.appendChild(link);
    objectTools.appendChild(item);
  }

  function enhanceBooleanCells() {
    const context = appAndModel();
    if (!context) return;
    addActionsHeader();
    addImportLink(context);
    document.querySelectorAll("#result_list tbody tr").forEach((row) => {
      addRecordActions(row, context);
      const cells = row.querySelectorAll("td[class*='field-']");
      cells.forEach((cell) => {
        const icon = cell.querySelector('img[alt="True"], img[alt="False"]');
        if (!icon) return;
        renderButton(cell, icon, context);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enhanceBooleanCells);
  } else {
    enhanceBooleanCells();
  }
})();
