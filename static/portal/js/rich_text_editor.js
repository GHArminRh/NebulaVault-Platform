(() => {
  "use strict";

  const CKEDITOR_VERSION = "49.0.0";
  const CKEDITOR_CSS = `https://cdn.ckeditor.com/ckeditor5/${CKEDITOR_VERSION}/ckeditor5.css`;
  const CKEDITOR_JS = `https://cdn.ckeditor.com/ckeditor5/${CKEDITOR_VERSION}/ckeditor5.umd.js`;
  const bootstrapScript = document.currentScript;
  const LICENSE_KEY = (bootstrapScript && bootstrapScript.dataset.licenseKey) || "GPL";
  const editorInstances = new Map();
  let bootPromise;

  const excludedSelector = [
    "textarea[data-no-rich-editor]",
    "textarea.no-rich-editor",
    "textarea[name*='json' i]",
    "textarea[name*='payload' i]",
    "textarea[name*='metadata' i]",
    "textarea[name*='config' i]",
    "textarea[name*='query' i]",
    "textarea[name*='code' i]",
    "textarea[name*='sql' i]"
  ].join(",");

  function loadStyles() {
    if (!document.querySelector('link[data-nv-ckeditor-css]')) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = CKEDITOR_CSS;
      link.dataset.nvCkeditorCss = "true";
      document.head.appendChild(link);
    }
    if (!document.querySelector('link[data-nv-rich-text-css]')) {
      const custom = document.createElement("link");
      custom.rel = "stylesheet";
      custom.href = "/static/portal/css/rich_text_editor.css";
      custom.dataset.nvRichTextCss = "true";
      document.head.appendChild(custom);
    }
  }

  function loadScript() {
    if (window.CKEDITOR && window.CKEDITOR.ClassicEditor) return Promise.resolve();
    if (bootPromise) return bootPromise;

    bootPromise = new Promise((resolve, reject) => {
      const existing = document.querySelector('script[data-nv-ckeditor-js]');
      if (existing) {
        existing.addEventListener("load", resolve, { once: true });
        existing.addEventListener("error", reject, { once: true });
        return;
      }
      const script = document.createElement("script");
      script.src = CKEDITOR_JS;
      script.async = true;
      script.dataset.nvCkeditorJs = "true";
      script.onload = resolve;
      script.onerror = () => reject(new Error("CKEditor 5 could not be loaded. Check your network connection or CDN access."));
      document.head.appendChild(script);
    });
    return bootPromise;
  }

  function shouldEnhance(textarea) {
    if (!(textarea instanceof HTMLTextAreaElement)) return false;
    if (textarea.disabled || textarea.readOnly || textarea.closest("[hidden], [data-no-rich-editor]")) return false;
    if (textarea.matches(excludedSelector) || ["true", "pending", "error"].includes(textarea.dataset.nvCkeditorReady)) return false;
    if (textarea.closest(".django-ckeditor-widget, .ck-editor")) return false;
    return true;
  }

  function makeEditorHost(textarea) {
    const host = document.createElement("div");
    host.className = "nv-ckeditor-host";
    host.dataset.nvCkeditorFor = textarea.id || textarea.name || "textarea";
    textarea.insertAdjacentElement("afterend", host);
    textarea.classList.add("nv-ckeditor-source");
    textarea.dataset.nvCkeditorReady = "true";
    return host;
  }

  function plainTextFromHtml(html) {
    const container = document.createElement("div");
    container.innerHTML = html;
    return (container.textContent || container.innerText || "").replace(/\u00a0/g, " ").trim();
  }

  function escapeHtml(value) {
    return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function normalizeInitialData(value) {
    if (!value) return "";
    // Keep existing rich HTML, but safely convert legacy plain-text values to paragraphs.
    if (/<\/?(p|h[1-6]|ul|ol|li|strong|b|em|i|u|a|blockquote|table|thead|tbody|tr|td|th|br|hr)\b/i.test(value)) {
      return value;
    }
    return value.replace(/\r\n?/g, "\n").split("\n")
      .map((line) => line ? `<p>${escapeHtml(line)}</p>` : "<p>&nbsp;</p>")
      .join("");
  }

  async function enhanceTextarea(textarea) {
    if (!shouldEnhance(textarea)) return;
    textarea.dataset.nvCkeditorReady = "pending";

    try {
      await loadScript();
      loadStyles();
      if (!textarea.isConnected || textarea.dataset.nvCkeditorReady !== "pending") return;

      const host = makeEditorHost(textarea);
      const required = textarea.required;
      textarea.dataset.nvCkeditorRequired = String(required);
      const originalAriaRequired = textarea.getAttribute("aria-required");
      textarea.required = false;

      const CK = window.CKEDITOR;
      const pluginNames = [
        "Essentials", "Paragraph", "Bold", "Italic", "Underline", "Strikethrough",
        "Link", "List", "BlockQuote", "Heading", "Table", "TableToolbar",
        "Font", "Alignment", "RemoveFormat"
      ];
      const plugins = pluginNames.map((name) => CK[name]).filter(Boolean);
      const toolbar = [
        "undo", "redo", "|", "heading", "|", "fontFamily", "fontSize", "fontColor",
        "fontBackgroundColor", "|", "bold", "italic", "underline", "strikethrough",
        "removeFormat", "|", "alignment", "|", "bulletedList", "numberedList",
        "outdent", "indent", "|", "link", "insertTable", "blockQuote"
      ];

      const editor = await CK.ClassicEditor.create(host, {
        licenseKey: LICENSE_KEY,
        plugins,
        toolbar: { items: toolbar, shouldNotGroupWhenFull: true },
        initialData: normalizeInitialData(textarea.value || ""),
        placeholder: textarea.getAttribute("placeholder") || "Start writing…",
        language: "en",
        table: { contentToolbar: ["tableColumn", "tableRow", "mergeTableCells"] },
        fontSize: { options: [10, 12, 14, "default", 18, 20, 24, 28, 32] },
        fontFamily: { supportAllValues: true },
        link: { addTargetToExternalLinks: true, defaultProtocol: "https://" }
      });

      editorInstances.set(textarea, editor);
      textarea._nvCkeditorEditor = editor;
      const sync = () => {
        const value = editor.getData();
        if (textarea.value !== value) {
          textarea.value = value;
          textarea.dispatchEvent(new Event("input", { bubbles: true }));
          textarea.dispatchEvent(new Event("change", { bubbles: true }));
        }
      };
      editor.model.document.on("change:data", () => {
        sync();
        const error = host.querySelector(".nv-ckeditor-validation-error");
        if (error && plainTextFromHtml(editor.getData())) error.remove();
        const editable = editor.ui.getEditableElement();
        if (editable && plainTextFromHtml(editor.getData())) editable.removeAttribute("aria-invalid");
      });

      if (required) {
        editor.editing.view.change((writer) => {
          writer.setAttribute("aria-required", "true", editor.editing.view.document.getRoot());
        });
        const editable = editor.ui.getEditableElement();
        if (editable) editable.setAttribute("aria-required", "true");
      }
      if (originalAriaRequired !== null) {
        const editable = editor.ui.getEditableElement();
        if (editable) editable.setAttribute("aria-required", originalAriaRequired);
      }

      const form = textarea.form;
      if (form && !form.dataset.nvCkeditorSubmitBound) {
        form.dataset.nvCkeditorSubmitBound = "true";
        form.addEventListener("submit", (event) => {
          const fields = Array.from(form.querySelectorAll("textarea[data-nv-ckeditor-ready='true']"));
          for (const field of fields) {
            const instance = editorInstances.get(field);
            if (!instance) continue;
            field.value = instance.getData();
            if (field.dataset.nvCkeditorRequired === "true" && !plainTextFromHtml(field.value)) {
              event.preventDefault();
              instance.editing.view.focus();
              const host = field.nextElementSibling;
              if (host && !host.querySelector(".nv-ckeditor-validation-error")) {
                const message = document.createElement("div");
                message.className = "nv-ckeditor-validation-error";
                message.setAttribute("role", "alert");
                message.textContent = "This field is required.";
                host.appendChild(message);
              }
              const editable = instance.ui.getEditableElement();
              if (editable) editable.setAttribute("aria-invalid", "true");
              return;
            }
          }
        }, true);
      }
      textarea.dataset.nvCkeditorReady = "true";
    } catch (error) {
      textarea.dataset.nvCkeditorReady = "error";
      textarea.classList.remove("nv-ckeditor-source");
      const host = textarea.nextElementSibling;
      if (host && host.classList.contains("nv-ckeditor-host")) host.remove();
      textarea.required = textarea.dataset.nvCkeditorRequired === "true";
      console.error("[Nebula Vault] CKEditor initialization failed:", error);
      const notice = document.createElement("div");
      notice.className = "nv-ckeditor-fallback-notice";
      notice.textContent = "Rich text editor unavailable; the standard text field is still available.";
      textarea.insertAdjacentElement("afterend", notice);
    }
  }

  function enhanceAll(root = document) {
    root.querySelectorAll("textarea").forEach((textarea) => {
      if (shouldEnhance(textarea)) void enhanceTextarea(textarea);
    });
  }

  function start() {
    enhanceAll();
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (!(node instanceof Element)) continue;
          if (node.matches("textarea") && shouldEnhance(node)) void enhanceTextarea(node);
          enhanceAll(node);
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
