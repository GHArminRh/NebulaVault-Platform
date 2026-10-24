(() => {
  "use strict";
  const VERSION = "48.5.1";
  const CDN_BASE = "https://cdn.ckeditor.com/ckeditor5/" + VERSION + "/";
  const PREMIUM_BASE = "https://cdn.ckeditor.com/ckeditor5-premium-features/" + VERSION + "/";
  const CORE_CSS = CDN_BASE + "ckeditor5.css";
  const PREMIUM_CSS = PREMIUM_BASE + "ckeditor5-premium-features.css";
  // Bundled CKEditor 5 Free production license for this private project.
  // License keys are client-side configuration; rotate it in the CKEditor portal if exposed publicly.
  const DEFAULT_LICENSE_KEY = "eyJhbGciOiJFUzI1NiJ9.eyJleHAiOjE4MjQ0MjIzOTksImp0aSI6ImVlYzcwOWUyLTgzMjAtNDljMS1hNzhjLWEyYzhmYTAzYTE0NyIsInVzYWdlRW5kcG9pbnQiOiJodHRwczovL3Byb3h5LWV2ZW50LmNrZWRpdG9yLmNvbSIsImRpc3RyaWJ1dGlvbkNoYW5uZWwiOlsiY2xvdWQiLCJkcnVwYWwiXSwiZmVhdHVyZXMiOlsiRFJVUCIsIkUyUCIsIkUyVyJdLCJyZW1vdmVGZWF0dXJlcyI6WyJQQiIsIlJGIiwiU0NIIiwiVENQIiwiVEwiLCJUQ1IiLCJJUiIsIlNVQSIsIkI2NEEiLCJMUCIsIkhFIiwiUkVEIiwiUEZPIiwiV0MiLCJGQVIiLCJCS00iLCJGUEgiLCJNUkUiLCJNRVIiXSwidmMiOiI4NmRjMzFmMiJ9.8WUmcBGvM7Ud6vvleU1FGMtPM1BWoEnG3rV5OJsbAanaX6CDdNtZkwSRm97fuOoDZW8n49qTkw0ceplWSFPiQw";
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
    const defaults = { licenseKey: DEFAULT_LICENSE_KEY, cloudServicesTokenUrl: "" };
    const node = document.getElementById("nebula-ckeditor-config");
    if (!node) return defaults;
    try {
      const config = JSON.parse(node.textContent || "{}");
      return {
        ...config,
        licenseKey: (config.licenseKey || "").trim() || DEFAULT_LICENSE_KEY,
        cloudServicesTokenUrl: (config.cloudServicesTokenUrl || "").trim()
      };
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

  function init(textarea, CK, Premium, runtimeConfig) {
    if (textarea.dataset.ckeditorInitialized === "true") return;
    textarea.dataset.ckeditorInitialized = "true";
    textarea.classList.add("nv-ckeditor-source");
    const host = document.createElement("div");
    host.className = "nv-ckeditor-host";
    textarea.insertAdjacentElement("afterend", host);
    const initialValue = textarea.value || "";
    const form = textarea.form;
    const tokenUrl = (runtimeConfig.cloudServicesTokenUrl || "").trim();

    const plugins = [
      CK.Alignment, CK.Autoformat, CK.AutoImage, CK.AutoLink, CK.Autosave, CK.BalloonToolbar,
      CK.BlockQuote, CK.Bold, CK.Code, CK.CodeBlock, CK.Essentials, CK.FindAndReplace,
      CK.FontBackgroundColor, CK.FontColor, CK.FontFamily, CK.FontSize, CK.Fullscreen,
      CK.GeneralHtmlSupport, CK.Heading, CK.Highlight, CK.HorizontalLine, CK.ImageBlock,
      CK.ImageCaption, CK.ImageEditing, CK.ImageInline, CK.ImageInsert, CK.ImageInsertViaUrl,
      CK.ImageResize, CK.ImageStyle, CK.ImageTextAlternative, CK.ImageToolbar, CK.ImageUpload,
      CK.ImageUtils, CK.Indent, CK.IndentBlock, CK.Italic, CK.Link, CK.LinkImage, CK.List,
      CK.ListProperties, CK.MediaEmbed, CK.Paragraph, CK.PasteFromOffice, CK.PictureEditing,
      CK.RemoveFormat, CK.ShowBlocks, CK.SpecialCharacters, CK.SpecialCharactersArrows,
      CK.SpecialCharactersCurrency, CK.SpecialCharactersEssentials, CK.SpecialCharactersLatin,
      CK.SpecialCharactersMathematical, CK.SpecialCharactersText, CK.Strikethrough, CK.Subscript,
      CK.Superscript, CK.Table, CK.TableCaption, CK.TableCellProperties, CK.TableColumnResize,
      CK.TableProperties, CK.TableToolbar, CK.TextTransformation, CK.TodoList, CK.Underline, CK.WordCount
    ];
    const toolbarItems = [
      "undo", "redo", "|", "showBlocks", "findAndReplace", "|", "heading", "|",
      "fontSize", "fontFamily", "fontColor", "fontBackgroundColor", "|",
      "bold", "italic", "underline", "strikethrough", "subscript", "superscript",
      "code", "removeFormat", "|", "specialCharacters", "horizontalLine", "link",
      "insertImage", "insertImageViaUrl", "mediaEmbed", "insertTable", "highlight",
      "blockQuote", "codeBlock", "|", "alignment", "bulletedList", "numberedList",
      "todoList", "outdent", "indent"
    ];
    const config = {
      licenseKey: runtimeConfig.licenseKey,
      placeholder: textarea.getAttribute("placeholder") || "Type or paste your content here…",
      plugins: plugins,
      extraPlugins: [NebulaUploadAdapterPlugin],
      toolbar: { items: toolbarItems, shouldNotGroupWhenFull: false },
      balloonToolbar: ["bold", "italic", "|", "link", "insertImage", "|", "bulletedList", "numberedList"],
      menuBar: { isVisible: true },
      autosave: {
        save: editor => { textarea.value = editor.getData(); return Promise.resolve(); },
        waitingTime: 1500
      },
      alignment: { options: ["left", "center", "right", "justify"] },
      fontFamily: { supportAllValues: true },
      fontSize: { options: [10, 12, 14, "default", 18, 20, 22], supportAllValues: true },
      heading: { options: [
        { model: "paragraph", title: "Paragraph", class: "ck-heading_paragraph" },
        { model: "heading1", view: "h1", title: "Heading 1", class: "ck-heading_heading1" },
        { model: "heading2", view: "h2", title: "Heading 2", class: "ck-heading_heading2" },
        { model: "heading3", view: "h3", title: "Heading 3", class: "ck-heading_heading3" },
        { model: "heading4", view: "h4", title: "Heading 4", class: "ck-heading_heading4" },
        { model: "heading5", view: "h5", title: "Heading 5", class: "ck-heading_heading5" },
        { model: "heading6", view: "h6", title: "Heading 6", class: "ck-heading_heading6" }
      ]},
      htmlSupport: { allow: [{ name: /^.*$/, styles: true, attributes: true, classes: true }] },
      image: { toolbar: [
        "toggleImageCaption", "imageTextAlternative", "|", "imageStyle:inline",
        "imageStyle:wrapText", "imageStyle:breakText", "|", "resizeImage"
      ]},
      link: {
        addTargetToExternalLinks: true, defaultProtocol: "https://",
        decorators: { toggleDownloadable: { mode: "manual", label: "Downloadable", attributes: { download: "file" } } }
      },
      list: { properties: { styles: true, startIndex: true, reversed: true } },
      table: { contentToolbar: ["tableColumn", "tableRow", "mergeTableCells", "tableProperties", "tableCellProperties"] },
      initialData: initialValue
    };

    // Free plan includes a small monthly quota for PDF/Word exports; the cloud token is required.
    if (tokenUrl && Premium && Premium.ExportPdf && Premium.ExportWord && CK.CloudServices) {
      plugins.push(CK.CloudServices, Premium.ExportPdf, Premium.ExportWord);
      toolbarItems.splice(3, 0, "exportWord", "exportPdf", "|");
      config.cloudServices = { tokenUrl: tokenUrl };
      config.exportPdf = {
        stylesheets: [CORE_CSS, PREMIUM_CSS], fileName: "nebula-vault-document.pdf",
        converterOptions: { format: "A4", margin_top: "20mm", margin_bottom: "20mm",
          margin_right: "20mm", margin_left: "20mm", page_orientation: "portrait" }
      };
      config.exportWord = {
        stylesheets: [CORE_CSS, PREMIUM_CSS], fileName: "nebula-vault-document.docx",
        converterOptions: { document: { orientation: "portrait", size: "A4",
          margins: { top: "20mm", bottom: "20mm", right: "20mm", left: "20mm" } } }
      };
      addStylesheet(PREMIUM_CSS);
    }

    CK.ClassicEditor.create(host, config).then(editor => {
      textarea.dataset.ckeditorReady = "true";
      textarea._nebulaCkeditor = editor;
      textarea.value = editor.getData();
      const wordCount = editor.plugins.get("WordCount");
      const count = document.createElement("div");
      count.className = "nv-ckeditor-word-count";
      count.appendChild(wordCount.wordCountContainer);
      host.appendChild(count);
      editor.model.document.on("change:data", () => { textarea.value = editor.getData(); });
      if (form) form.addEventListener("submit", () => { textarea.value = editor.getData(); }, true);
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
      const tokenUrl = (runtimeConfig.cloudServicesTokenUrl || "").trim();
      if (tokenUrl) {
        await loadScript(PREMIUM_BASE + "ckeditor5-premium-features.umd.js");
        const Premium = window.CKEDITOR_PREMIUM_FEATURES || {};
        fields.forEach(field => init(field, CK, Premium, runtimeConfig));
      } else {
        fields.forEach(field => init(field, CK, {}, runtimeConfig));
      }
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
