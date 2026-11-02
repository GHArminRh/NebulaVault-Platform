(() => {
  "use strict";

  const formatBytes = (bytes) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  const initializeUploader = (root) => {
    if (root.dataset.nvReady === "true") return;
    root.dataset.nvReady = "true";

    const input = root.querySelector("[data-nv-image-input]");
    const dropzone = root.querySelector("[data-dropzone]");
    const selection = root.querySelector("[data-selection]");
    const preview = root.querySelector("[data-preview-image]");
    const filename = root.querySelector("[data-file-name]");
    const filesize = root.querySelector("[data-file-size]");
    const current = root.querySelector("[data-current-preview]");
    const message = root.querySelector("[data-uploader-message]");
    const maxBytes = Number(root.dataset.maxBytes || 0);
    let previewUrl = null;

    if (!input || !dropzone) return;

    const showMessage = (text, isError) => {
      message.textContent = text || "";
      message.classList.toggle("is-error", Boolean(isError));
      message.classList.toggle("is-success", Boolean(text) && !isError);
    };

    const releasePreview = () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = null;
    };

    const setFile = (file) => {
      showMessage("", false);
      if (!file) return;
      if (!file.type || !file.type.startsWith("image/")) {
        input.value = "";
        showMessage("Please choose a valid image file.", true);
        return;
      }
      if (maxBytes && file.size > maxBytes) {
        input.value = "";
        showMessage("This image exceeds the 12 MB upload limit.", true);
        return;
      }

      releasePreview();
      previewUrl = URL.createObjectURL(file);
      preview.src = previewUrl;
      filename.textContent = file.name;
      filesize.textContent = formatBytes(file.size);
      selection.hidden = false;
      if (current) current.hidden = true;
      root.dataset.hasSelection = "true";
    };

    input.addEventListener("change", () => setFile(input.files && input.files[0]));

    dropzone.addEventListener("click", (event) => {
      if (event.target.closest("button")) return;
      input.click();
    });
    dropzone.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        input.click();
      }
    });

    ["dragenter", "dragover"].forEach((name) => {
      dropzone.addEventListener(name, (event) => {
        event.preventDefault();
        event.stopPropagation();
        dropzone.classList.add("is-dragover");
      });
    });
    ["dragleave", "dragend", "drop"].forEach((name) => {
      dropzone.addEventListener(name, (event) => {
        event.preventDefault();
        event.stopPropagation();
        dropzone.classList.remove("is-dragover");
      });
    });
    dropzone.addEventListener("drop", (event) => {
      const file = event.dataTransfer && event.dataTransfer.files[0];
      if (!file) return;
      try {
        const transfer = new DataTransfer();
        transfer.items.add(file);
        input.files = transfer.files;
        setFile(file);
      } catch (error) {
        showMessage("Your browser could not attach this dropped file. Please browse for it instead.", true);
      }
    });

    const remove = root.querySelector("[data-remove-selection]");
    if (remove) {
      remove.addEventListener("click", () => {
        input.value = "";
        selection.hidden = true;
        if (current) current.hidden = false;
        root.dataset.hasSelection = "false";
        releasePreview();
        showMessage("", false);
      });
    }
  };

  const setUploadState = (root, state, percent, statusText) => {
    const panel = root.querySelector("[data-upload-panel]");
    const bar = root.querySelector("[data-upload-bar]");
    const track = root.querySelector("[data-upload-progress]");
    const label = root.querySelector("[data-upload-label]");
    const percentLabel = root.querySelector("[data-upload-percent]");
    const status = root.querySelector("[data-upload-status]");
    if (!panel) return;

    panel.hidden = false;
    root.dataset.uploadState = state;
    bar.style.width = percent + "%";
    track.setAttribute("aria-valuenow", String(percent));
    percentLabel.textContent = percent + "%";
    label.textContent = state === "complete" ? "Upload complete" :
      state === "failed" ? "Upload failed" : "Uploading image…";
    status.textContent = statusText;
  };

  const submitWithProgress = (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.querySelector("[data-nv-image-uploader]")) return;
    if (event.defaultPrevented) return;

    event.preventDefault();
    event.stopImmediatePropagation();

    const submitter = event.submitter;
    const data = new FormData(form);
    if (submitter && submitter.name && !submitter.disabled) {
      data.append(submitter.name, submitter.value);
    }

    const roots = Array.from(form.querySelectorAll("[data-nv-image-uploader]"));
    const buttons = Array.from(form.querySelectorAll("button[type='submit'], input[type='submit']"));
    const originalDisabled = buttons.map((button) => button.disabled);
    buttons.forEach((button) => { button.disabled = true; });
    form.setAttribute("aria-busy", "true");

    roots.forEach((root) => {
      const input = root.querySelector("[data-nv-image-input]");
      const file = input && input.files && input.files[0];
      if (file) {
        const state = root.querySelector("[data-file-state]");
        if (state) state.textContent = "Uploading…";
      }
      setUploadState(root, "uploading", 0, "Preparing secure upload…");
    });

    const xhr = new XMLHttpRequest();
    xhr.open((form.method || "POST").toUpperCase(), form.action || window.location.href, true);
    xhr.withCredentials = true;
    xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");

    xhr.upload.addEventListener("progress", (progressEvent) => {
      if (!progressEvent.lengthComputable) return;
      const percent = Math.min(99, Math.round((progressEvent.loaded / progressEvent.total) * 100));
      roots.forEach((root) => {
        setUploadState(root, "uploading", percent, "Sending " +
          formatBytes(progressEvent.loaded) + " of " + formatBytes(progressEvent.total));
      });
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 400) {
        roots.forEach((root) => {
          setUploadState(root, "complete", 100, "Upload received. Finishing save…");
        });
        const destination = xhr.responseURL || window.location.href;
        if (destination !== window.location.href) {
          window.location.assign(destination);
          return;
        }
        document.open();
        document.write(xhr.responseText);
        document.close();
        return;
      }

      roots.forEach((root) => {
        setUploadState(root, "failed", 0, "The server rejected the upload. Your form is still available.");
        const message = root.querySelector("[data-uploader-message]");
        if (message) {
          message.textContent = "Upload failed (HTTP " + xhr.status + "). Please review the form and try again.";
          message.classList.add("is-error");
        }
      });
      buttons.forEach((button, index) => { button.disabled = originalDisabled[index]; });
      form.removeAttribute("aria-busy");
    });

    xhr.addEventListener("error", () => {
      roots.forEach((root) => {
        setUploadState(root, "failed", 0, "Network error. Check your connection and try again.");
      });
      buttons.forEach((button, index) => { button.disabled = originalDisabled[index]; });
      form.removeAttribute("aria-busy");
    });

    xhr.addEventListener("abort", () => {
      roots.forEach((root) => setUploadState(root, "failed", 0, "Upload cancelled."));
      buttons.forEach((button, index) => { button.disabled = originalDisabled[index]; });
      form.removeAttribute("aria-busy");
    });

    xhr.send(data);
  };

  const initialize = () => {
    document.querySelectorAll("[data-nv-image-uploader]").forEach(initializeUploader);
    document.addEventListener("submit", submitWithProgress, true);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();
