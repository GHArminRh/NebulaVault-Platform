(() => {
  "use strict";

  const endpoint = "/admin/quick-toggle/";
  const protectedFields = new Set(["is_staff", "is_superuser"]);
  const actionCellClass = "nv-record-actions";

  function csrfToken() {
    const cookie = document.cookie.split("; ").find((part) => part.startsWith("csrftoken="));
    const formToken = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return cookie
      ? decodeURIComponent(cookie.split("=").slice(1).join("="))
      : (formToken ? formToken.value : "");
  }

  function addSwitchStyles() {
    if (document.getElementById("nv-admin-switch-styles")) return;
    const style = document.createElement("style");
    style.id = "nv-admin-switch-styles";
    style.textContent = `
      .nv-boolean-toggle {
        appearance: none; -webkit-appearance: none; display: inline-flex;
        align-items: center; justify-content: center; padding: 5px 7px; margin: 0;
        border: 0; border-radius: 9px; background: transparent; color: inherit;
        cursor: pointer; vertical-align: middle; touch-action: manipulation;
        transition: background-color .18s ease, opacity .18s ease;
      }
      .nv-boolean-toggle:hover { background: rgba(120, 145, 180, .10); }
      .nv-boolean-toggle:focus-visible { outline: 2px solid #4b9cff; outline-offset: 2px; }
      .nv-boolean-toggle:disabled { cursor: pointer; opacity: .78; }
      .nv-switch-track {
        position: relative; display: inline-block; flex: 0 0 34px;
        width: 34px; height: 20px; border-radius: 999px;
        background: #a3aab7; box-shadow: inset 0 0 0 1px rgba(0,0,0,.08);
        transition: background-color .22s cubic-bezier(.2,.8,.2,1), box-shadow .22s ease;
      }
      .nv-switch-thumb {
        position: absolute; top: 3px; left: 3px; width: 14px; height: 14px;
        border-radius: 50%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.22);
        transform: translateX(0); transition: transform .22s cubic-bezier(.2,.8,.2,1);
      }
      .nv-boolean-toggle.is-on .nv-switch-track {
        background: #2ca66f; box-shadow: inset 0 0 0 1px rgba(0,0,0,.05);
      }
      .nv-boolean-toggle.is-on .nv-switch-thumb { transform: translateX(14px); }
      .nv-boolean-toggle.is-saving .nv-switch-track { box-shadow: 0 0 0 2px rgba(75,156,255,.16); }
      @media (prefers-reduced-motion: reduce) {
        .nv-boolean-toggle, .nv-switch-track, .nv-switch-thumb { transition: none !important; }
      }
    `;
    document.head.appendChild(style);
  }

  function objectIdForRow(row) {
    if (!row) return null;
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
    if (cell.querySelector(".nv-boolean-toggle")) return;
    const fieldClass = Array.from(cell.classList).find((name) => name.startsWith("field-"));
    if (!fieldClass) return;
    const fieldName = fieldClass.slice("field-".length);
    if (!fieldName || protectedFields.has(fieldName)) return;

    const initialValue = icon.alt === "True";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "nv-boolean-toggle" + (initialValue ? " is-on" : "");
    button.setAttribute("role", "switch");
    button.setAttribute("aria-checked", String(initialValue));
    button.setAttribute("aria-label", (initialValue ? "Enabled" : "Disabled") + "; click to toggle");
    button.title = initialValue ? "Click to disable" : "Click to enable";
    button.dataset.value = String(initialValue);

    const track = document.createElement("span");
    track.className = "nv-switch-track";
    track.setAttribute("aria-hidden", "true");
    const thumb = document.createElement("span");
    thumb.className = "nv-switch-thumb";
    track.appendChild(thumb);
    button.appendChild(track);

    function paint(value) {
      button.dataset.value = String(value);
      button.classList.toggle("is-on", value);
      button.setAttribute("aria-checked", String(value));
      button.setAttribute("aria-label", (value ? "Enabled" : "Disabled") + "; click to toggle");
      button.title = value ? "Click to disable" : "Click to enable";
    }

    let pending = false;
    button.addEventListener("click", async () => {
      if (pending) return;
      const previousValue = button.dataset.value === "true";
      const nextValue = !previousValue;
      const objectId = objectIdForRow(cell.closest("tr"));
      if (!objectId) {
        window.alert("Could not identify this record. Refresh the page and try again.");
        return;
      }

      pending = true;
      button.disabled = true;
      button.classList.add("is-saving");
      paint(nextValue); // Immediate, optimistic UI update; the server remains authoritative.
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
            object_id: objectId,
            field_name: fieldName,
            value: nextValue
          })
        });
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || "Could not save this change.");
        paint(Boolean(data.value));
      } catch (error) {
        paint(previousValue);
        window.alert(error.message || "Could not save this change.");
      } finally {
        pending = false;
        button.disabled = false;
        button.classList.remove("is-saving");
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
    cell.style.cssText = "white-space:nowrap;text-align:center;vertical-align:middle;";

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
    deleteIcon.style.cssText = "width:10px;height:10px;display:inline-block;vertical-align:middle;border:0;";
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
    exportIcon.style.cssText = "width:10px;height:10px;display:inline-block;vertical-align:middle;border:0;";
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
    addSwitchStyles();
    addActionsHeader();
    addImportLink(context);
    document.querySelectorAll("#result_list tbody tr").forEach((row) => {
      addRecordActions(row, context);
      row.querySelectorAll("td[class*='field-']").forEach((cell) => {
        const icon = cell.querySelector('img[alt="True"], img[alt="False"]');
        if (icon) renderButton(cell, icon, context);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enhanceBooleanCells);
  } else {
    enhanceBooleanCells();
  }
})();
