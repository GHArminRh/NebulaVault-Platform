(() => {
  "use strict";
  const VERSION = "48.5.1";
  const CDN_BASE = "https://cdn.ckeditor.com/ckeditor5/" + VERSION + "/";
  const CORE_CSS = CDN_BASE + "ckeditor5.css";
  // Commercial free-plan key is browser-visible by design. Restrict it to approved hosts in the CKEditor portal.
  const DEFAULT_LICENSE_KEY = "eyJhbGciOiJFUzI1NiJ9.eyJleHAiOjE4MjQ0MjIzOTksImp0aSI6IjI0ZDQ0ZjFmLTFmMDgtNGQyNS05ZWRjLWFjZDc2OGRjNzdkMiIsImxpY2Vuc2VkSG9zdHMiOlsiMTI3LjAuMC4xIl0sInVzYWdlRW5kcG9pbnQiOiJodHRwczovL3Byb3h5LWV2ZW50LmNrZWRpdG9yLmNvbSIsImRpc3RyaWJ1dGlvbkNoYW5uZWwiOlsiY2xvdWQiLCJkcnVwYWwiXSwiZmVhdHVyZXMiOlsiRFJVUCIsIkUyUCIsIkUyVyJdLCJyZW1vdmVGZWF0dXJlcyI6WyJQQiIsIlJGIiwiU0NIIiwiVENQIiwiVEwiLCJUQ1IiLCJJUiIsIlNVQSIsIkI2NEEiLCJMUCIsIkhFIiwiUkVEIiwiUEZPIiwiV0MiLCJGQVIiLCJCS00iLCJGUEgiLCJNUkUiLCJNRVIiXSwidmMiOiJmYjA1YTU3OCJ9.U7s7YoQbpfpPhMidJTjPg6Xf0LyF8I2SYFp-iySYGaCHY2dkXVLRHoUL3yuo2HqCRozpSgl3Odq6Z0z9hQgTqg";
  const EXCLUDED = [
    "textarea[data-no-rich-editor]", "textarea.no-rich-editor",
    "textarea[name*='json' i]", "textarea[name*='payload' i]",
    "textarea[name*='metadata' i]", "textarea[name*='config' i]",
    "textarea[name*='query' i]", "textarea[name*='code' i]",
    "textarea[name*='sql' i]", "textarea[name*='token' i]",
    "textarea[name*='secret' i]", "textarea[name*='key' i]"
  ].join(",");
  const ELIGIBLE = [
    "textarea[data-rich-editor]", "textarea.rich-text",
    "textarea[name='description']", "textarea[name='release_notes']",
    "textarea[name='content']", "textarea[name='body']",
    "textarea[name='terms']", "textarea[name='policy']"
  ].join(",");

  function getRuntimeConfig() {
    const defaults = { licenseKey: DEFAULT_LICENSE_KEY };
    const node = document.getElementById("nebula-ckeditor-config");
    if (!node) return defaults;
    try {
      const config = JSON.parse(node.textContent || "{}");
      return { ...config, licenseKey: (config.licenseKey || "").trim() || DEFAULT_LICENSE_KEY };
    } catch (error) {
      console.error("Unable to parse CKEditor configuration; using bundled license defaults:", error);
      return defaults;
    }
  }

  function addStylesheet(href) {
    if ([...document.querySelectorAll('link[rel="stylesheet"]')].some(link => link.href === href)) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.crossOrigin = "anonymous";
    document.head.appendChild(link);
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = src;
      script.crossOrigin = "anonymous";
      script.onload = resolve;
      script.onerror = () => reject(new Error("Unable to load script: " + src));
      document.head.appendChild(script);
    });
  }

  function getCookie(name) {
    const entry = document.cookie.split(";").map(value => value.trim()).find(value => value.startsWith(name + "="));
    return entry ? decodeURIComponent(entry.slice(name.length + 1)) : "";
  }

  class NebulaUploadAdapter {
    constructor(loader) { this.loader = loader; this.xhr = null; }
    upload() {
      return this.loader.file.then(file => new Promise((resolve, reject) => {
        const xhr = this.xhr = new XMLHttpRequest();
        xhr.open("POST", "/admin/editor-upload/", true);
        xhr.responseType = "json";
        xhr.setRequestHeader("X-CSRFToken", getCookie("csrftoken"));
        xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
        xhr.addEventListener("error", () => reject("Image upload failed because of a network error."));
        xhr.addEventListener("abort", () => reject("Image upload was aborted."));
        xhr.addEventListener("load", () => {
          const response = xhr.response || {};
          if (xhr.status >= 200 && xhr.status < 300 && response.url) resolve({ default: response.url });
          else reject(response.error || "Image upload failed. Check staff access and server logs.");
        });
        const data = new FormData();
        data.append("upload", file);
        xhr.send(data);
      }));
    }
    abort() { if (this.xhr) this.xhr.abort(); }
  }

  function NebulaUploadAdapterPlugin(editor) {
    editor.plugins.get("FileRepository").createUploadAdapter = loader => new NebulaUploadAdapter(loader);
  }

  function init(textarea, CK, runtimeConfig) {
    if (textarea.dataset.ckeditorInitialized === "true") return;
    textarea.dataset.ckeditorInitialized = "true";
    textarea.classList.add("nv-ckeditor-source");
    const host = document.createElement("div");
    host.className = "nv-ckeditor-host";
    textarea.insertAdjacentElement("afterend", host);
    const form = textarea.form;

    // Keep this list limited to standard editing plugins; premium and explicitly
    // excluded free-plan features (e.g. Find & Replace, Remove Format and List
    // Properties) are intentionally not registered.
    const pluginNames = [
      // Core editing and text formatting available on the commercial Free plan.
      "Essentials", "Paragraph", "Bold", "Italic", "Underline", "Strikethrough",
      "Subscript", "Superscript", "Font", "Heading", "Style", "Alignment",
      "Indent", "IndentBlock", "BlockQuote", "HorizontalLine", "Link", "AutoLink",
      "List", "TodoList", "Autoformat", "CodeBlock", "SelectAll", "PasteFromPlainText",
      "CaseChange", "Emoji",
      // Tables and media. Paid table-property and image-resize features are deliberately omitted.
      "Table", "TableToolbar", "TableCaption", "MediaEmbed", "Image", "ImageInsert", "ImageToolbar",
      "ImageCaption", "ImageStyle", "ImageUpload", "LinkImage",
      // Free-plan HTML and navigation tools. The toolbar entries are added only when available.
      "GeneralHtmlSupport", "ShowBlocks", "SourceEditing"
    ];
    const plugins = pluginNames.map(name => CK[name]).filter(Boolean);
    plugins.push(NebulaUploadAdapterPlugin);

    const toolbarCandidates = [
      "undo", "redo", "|", "heading", "style", "|", "bold", "italic", "underline",
      "strikethrough", "subscript", "superscript", "|", "fontSize", "fontFamily",
      "fontColor", "fontBackgroundColor", "caseChange", "|", "alignment",
      "|", "bulletedList", "numberedList", "todoList", "outdent", "indent", "|",
      "link", "uploadImage", "insertImage", "mediaEmbed", "insertTable", "|", "blockQuote",
      "horizontalLine", "codeBlock", "emoji", "selectAll", "showBlocks", "sourceEditing"
    ];
    const available = new Set();
    const toolbarMap = [
      ["Essentials", ["undo", "redo", "selectAll"]], ["Heading", ["heading"]],
      ["Style", ["style"]], ["Bold", ["bold"]], ["Italic", ["italic"]],
      ["Underline", ["underline"]], ["Strikethrough", ["strikethrough"]],
      ["Subscript", ["subscript"]], ["Superscript", ["superscript"]],
      ["Font", ["fontSize", "fontFamily", "fontColor", "fontBackgroundColor"]],
      ["CaseChange", ["caseChange"]],
      ["Alignment", ["alignment"]], ["List", ["bulletedList", "numberedList"]],
      ["TodoList", ["todoList"]], ["Indent", ["outdent", "indent"]],
      ["Link", ["link"]], ["ImageUpload", ["uploadImage"]], ["ImageInsert", ["insertImage"]], ["MediaEmbed", ["mediaEmbed"]],
      ["Table", ["insertTable"]], ["BlockQuote", ["blockQuote"]],
      ["HorizontalLine", ["horizontalLine"]], ["CodeBlock", ["codeBlock"]],
      ["Emoji", ["emoji"]], ["ShowBlocks", ["showBlocks"]], ["SourceEditing", ["sourceEditing"]]
    ];
    toolbarMap.forEach(([pluginName, items]) => {
      if (CK[pluginName]) items.forEach(item => available.add(item));
    });
    const toolbarItems = toolbarCandidates.filter(item => item === "|" || available.has(item));
    while (toolbarItems[0] === "|") toolbarItems.shift();
    while (toolbarItems[toolbarItems.length - 1] === "|") toolbarItems.pop();
    for (let i = toolbarItems.length - 1; i > 0; i--) {
      if (toolbarItems[i] === "|" && toolbarItems[i - 1] === "|") toolbarItems.splice(i, 1);
    }

    const config = {
      licenseKey: runtimeConfig.licenseKey,
      placeholder: textarea.getAttribute("placeholder") || "Type or paste your content here…",
      plugins,
      toolbar: { items: toolbarItems, shouldNotGroupWhenFull: false },
      image: { toolbar: ["imageTextAlternative", "toggleImageCaption", "imageStyle:inline", "imageStyle:block", "imageStyle:side"] },
      table: { contentToolbar: ["tableColumn", "tableRow", "mergeTableCells"] },
      style: { definitions: [
        { name: "Lead paragraph", element: "p", classes: ["nv-lead"] },
        { name: "Highlighted text", element: "span", classes: ["nv-highlight"] },
        { name: "Small text", element: "span", classes: ["nv-small"] }
      ] },
      link: { addTargetToExternalLinks: true, defaultProtocol: "https://" },
      autosave: {
        save: editor => { textarea.value = editor.getData(); return Promise.resolve(); },
        waitingTime: 1500
      },
      initialData: textarea.value || ""
    };

    CK.ClassicEditor.create(host, config).then(editor => {
      textarea.dataset.ckeditorReady = "true";
      textarea._nebulaCkeditor = editor;
      textarea.value = editor.getData();
      editor.model.document.on("change:data", () => { textarea.value = editor.getData(); });

      // Fullscreen is implemented locally so it works without CKEditor's paid Fullscreen add-on.
      const fullscreenButton = document.createElement("button");
      fullscreenButton.type = "button";
      fullscreenButton.className = "nv-ckeditor-fullscreen-button";
      fullscreenButton.textContent = "⛶";
      fullscreenButton.title = "Expand editor";
      fullscreenButton.setAttribute("aria-label", "Expand editor");
      fullscreenButton.setAttribute("aria-pressed", "false");
      const toolbarItemsElement = editor.ui.view.toolbar.element.querySelector(".ck-toolbar__items");
      if (toolbarItemsElement) toolbarItemsElement.appendChild(fullscreenButton);
      const setFullscreen = enabled => {
        host.classList.toggle("nv-ckeditor-fullscreen", enabled);
        fullscreenButton.setAttribute("aria-pressed", String(enabled));
        fullscreenButton.setAttribute("aria-label", enabled ? "Exit fullscreen" : "Expand editor");
        fullscreenButton.title = enabled ? "Exit fullscreen (Esc)" : "Expand editor";
        fullscreenButton.textContent = enabled ? "×" : "⛶";
        document.body.classList.toggle("nv-ckeditor-fullscreen-active", enabled);
        if (enabled) editor.editing.view.focus();
      };
      fullscreenButton.addEventListener("click", () => {
        setFullscreen(!host.classList.contains("nv-ckeditor-fullscreen"));
      });
      const handleFullscreenEscape = event => {
        if (event.key === "Escape" && host.classList.contains("nv-ckeditor-fullscreen")) setFullscreen(false);
      };
      document.addEventListener("keydown", handleFullscreenEscape);
      if (form) form.addEventListener("submit", () => {
        if (!editor.isReadOnly) textarea.value = editor.getData();
      }, true);

      let readOnlyNotice = null;
      const handleReadOnlyState = () => {
        if (!editor.isReadOnly) {
          if (readOnlyNotice) readOnlyNotice.remove();
          readOnlyNotice = null;
          return;
        }
        textarea.value = editor.getData();
        textarea.classList.remove("nv-ckeditor-source");
        if (!readOnlyNotice) {
          readOnlyNotice = document.createElement("p");
          readOnlyNotice.className = "nv-ckeditor-error";
          readOnlyNotice.setAttribute("role", "alert");
          readOnlyNotice.textContent = "CKEditor is in read-only mode. The original text field is available below as a fallback. Check the browser Console for CKEditor license validation or usage-limit errors.";
          host.insertAdjacentElement("beforebegin", readOnlyNotice);
        }
        console.error("CKEditor entered read-only mode. Check for license-key-usage-limit, license-key-domain-limit, license-key-validation-endpoint-not-reachable, or other CKEditor license errors.");
      };
      editor.on("change:isReadOnly", handleReadOnlyState);
      handleReadOnlyState();
    }).catch(error => {
      console.error("CKEditor 5 failed to initialize:", error);
      host.remove();
      textarea.classList.remove("nv-ckeditor-source");
      textarea.dataset.ckeditorInitialized = "false";
      const message = document.createElement("p");
      message.className = "nv-ckeditor-error";
      message.textContent = "CKEditor could not start. Check the browser console and CKEditor license configuration.";
      textarea.insertAdjacentElement("afterend", message);
    });
  }

  async function start() {
    const fields = [...document.querySelectorAll(ELIGIBLE)].filter(el => !el.matches(EXCLUDED));
    if (!fields.length) return;
    const runtimeConfig = getRuntimeConfig();
    if (!runtimeConfig.licenseKey) {
      const message = document.createElement("p");
      message.className = "nv-ckeditor-notice";
      message.setAttribute("role", "status");
      message.textContent = "CKEditor license configuration is missing. The standard text field remains available.";
      fields[0].insertAdjacentElement("beforebegin", message);
      console.error("CKEditor is not initialized: no license key is available.");
      return;
    }
    addStylesheet(CORE_CSS);
    try {
      await loadScript(CDN_BASE + "ckeditor5.umd.js");
      const CK = window.CKEDITOR || {};
      fields.forEach(field => init(field, CK, runtimeConfig));
    } catch (error) {
      console.error("Unable to load CKEditor 5 from the configured CDN:", error);
      const message = document.createElement("p");
      message.className = "nv-ckeditor-error";
      message.setAttribute("role", "alert");
      message.textContent = "Rich-text editor could not load from the CKEditor CDN. Check the internet connection, browser extensions, Content Security Policy, and the browser Console/Network panels.";
      fields.forEach(field => field.insertAdjacentElement("beforebegin", message.cloneNode(true)));
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();