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

  function init(textarea, CK, runtimeConfig, allPlugins) {
    if (textarea.dataset.ckeditorInitialized === "true") return;
    textarea.dataset.ckeditorInitialized = "true";
    textarea.classList.add("nv-ckeditor-source");
    const host = document.createElement("div");
    host.className = "nv-ckeditor-host";
    textarea.insertAdjacentElement("afterend", host);
    const form = textarea.form;

    // Configuration follows the supplied CKEditor Builder sample. Only features
    // excluded by the existing license are omitted; the existing license itself is unchanged.
    const pluginNames = [
      "Essentials", "Paragraph", "Alignment", "AutoImage", "Autoformat", "AutoLink",
      "BlockQuote", "Bold", "Code", "CodeBlock", "Emoji", "ExportPdf", "ExportWord",
      "FontBackgroundColor", "FontColor", "FontFamily", "FontSize", "GeneralHtmlSupport",
      "Heading", "Highlight", "HorizontalLine", "ImageBlock", "ImageCaption",
      "ImageEditing", "ImageInline", "ImageInsert", "ImageInsertViaUrl", "ImageStyle",
      "ImageTextAlternative", "ImageToolbar", "ImageUtils",
      "Indent", "IndentBlock", "Italic", "Link", "LinkImage", "List", "MediaEmbed",
      "ShowBlocks", "Strikethrough", "Subscript", "Superscript", "Table",
      "TableCaption", "TableToolbar", "TextTransformation", "TodoList", "Underline"
    ];
    const plugins = [...new Set(pluginNames.map(name => allPlugins[name]).filter(Boolean))];

    const toolbar = [
      "undo", "redo", "|", "exportWord", "exportPdf", "showBlocks", "|",
      "heading", "|", "fontSize", "fontFamily", "fontColor", "fontBackgroundColor", "|",
      "bold", "italic", "underline", "strikethrough", "subscript", "superscript", "code", "|",
      "emoji", "horizontalLine", "link", "insertImage", "insertImageViaUrl",
      "mediaEmbed", "insertTable", "highlight", "blockQuote", "codeBlock", "|",
      "alignment", "|", "bulletedList", "numberedList", "todoList", "outdent", "indent"
    ];
    const toolbarPluginMap = {
      undo: "Essentials", redo: "Essentials", exportWord: "ExportWord", exportPdf: "ExportPdf",
      showBlocks: "ShowBlocks", heading: "Heading", fontSize: "FontSize", fontFamily: "FontFamily",
      fontColor: "FontColor", fontBackgroundColor: "FontBackgroundColor", bold: "Bold",
      italic: "Italic", underline: "Underline", strikethrough: "Strikethrough",
      subscript: "Subscript", superscript: "Superscript", code: "Code", emoji: "Emoji",
      horizontalLine: "HorizontalLine", link: "Link",
      insertImage: "ImageInsert", insertImageViaUrl: "ImageInsertViaUrl", mediaEmbed: "MediaEmbed",
      insertTable: "Table", highlight: "Highlight", blockQuote: "BlockQuote",
      codeBlock: "CodeBlock", alignment: "Alignment", bulletedList: "List",
      numberedList: "List", todoList: "TodoList", outdent: "Indent", indent: "Indent"
    };
    const availablePlugins = new Set(plugins);
    const toolbarItems = toolbar.filter(item =>
      item === "|" || availablePlugins.has(allPlugins[toolbarPluginMap[item]])
    );
    while (toolbarItems[0] === "|") toolbarItems.shift();
    while (toolbarItems[toolbarItems.length - 1] === "|") toolbarItems.pop();
    for (let i = toolbarItems.length - 1; i > 0; i--) {
      if (toolbarItems[i] === "|" && toolbarItems[i - 1] === "|") toolbarItems.splice(i, 1);
    }

    const config = {
      licenseKey: runtimeConfig.licenseKey,
      placeholder: textarea.getAttribute("placeholder") || "Type or paste your content here!",
      plugins,
      toolbar: { items: toolbarItems, shouldNotGroupWhenFull: false },
      alignment: { options: ["left", "center", "right", "justify"] },
      fontFamily: { supportAllValues: true },
      fontSize: { options: [10, 12, 14, "default", 18, 20, 22], supportAllValues: true },
      image: {
        toolbar: [
          "toggleImageCaption", "imageTextAlternative", "|",
          "imageStyle:inline", "imageStyle:wrapText", "imageStyle:breakText"
        ]
      },
      table: { contentToolbar: ["tableColumn", "tableRow", "mergeTableCells"] },
      exportPdf: {
        stylesheets: [CORE_CSS],
        fileName: "nebula-vault-document.pdf",
        converterOptions: {
          format: "Tabloid", margin_top: "20mm", margin_bottom: "20mm",
          margin_right: "24mm", margin_left: "24mm", page_orientation: "portrait"
        }
      },
      exportWord: {
        stylesheets: [CORE_CSS],
        fileName: "nebula-vault-document.docx",
        converterOptions: {
          document: {
            orientation: "portrait", size: "Tabloid",
            margins: { top: "20mm", bottom: "20mm", right: "24mm", left: "24mm" }
          }
        }
      },
      fontColor: { columns: 5, documentColors: 10 },
      fontBackgroundColor: { columns: 5, documentColors: 10 },
      heading: {
        options: [
          { model: "paragraph", title: "Paragraph", class: "ck-heading_paragraph" },
          { model: "heading1", view: "h1", title: "Heading 1", class: "ck-heading_heading1" },
          { model: "heading2", view: "h2", title: "Heading 2", class: "ck-heading_heading2" },
          { model: "heading3", view: "h3", title: "Heading 3", class: "ck-heading_heading3" },
          { model: "heading4", view: "h4", title: "Heading 4", class: "ck-heading_heading4" },
          { model: "heading5", view: "h5", title: "Heading 5", class: "ck-heading_heading5" },
          { model: "heading6", view: "h6", title: "Heading 6", class: "ck-heading_heading6" }
        ]
      },
      htmlSupport: {
        allow: [{ name: /^.*$/, styles: true, attributes: true, classes: true }]
      },
      link: {
        addTargetToExternalLinks: true,
        defaultProtocol: "https://",
        decorators: {
          toggleDownloadable: {
            mode: "manual", label: "Downloadable", attributes: { download: "file" }
          }
        }
      },
      menuBar: { isVisible: true },
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
    addStylesheet("https://cdn.ckeditor.com/ckeditor5-premium-features/" + VERSION + "/ckeditor5-premium-features.css");
    try {
      await loadScript(CDN_BASE + "ckeditor5.umd.js");
      await loadScript("https://cdn.ckeditor.com/ckeditor5-premium-features/" + VERSION + "/ckeditor5-premium-features.umd.js");
      const CK = window.CKEDITOR || {};
      const allPlugins = { ...CK, ...(window.CKEDITOR_PREMIUM_FEATURES || {}) };
      fields.forEach(field => init(field, CK, runtimeConfig, allPlugins));
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