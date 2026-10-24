(() => {
  "use strict";
  const VERSION = "48.5.1";
  const CORE_CSS = "https://cdn.ckeditor.com/ckeditor5/" + VERSION + "/ckeditor5.css";
  const PREMIUM_CSS = "https://cdn.ckeditor.com/ckeditor5-premium-features/" + VERSION + "/ckeditor5-premium-features.css";
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

  function addStylesheet(href) {
    if ([...document.styleSheets].some(sheet => sheet.href === href)) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.crossOrigin = "anonymous";
    document.head.appendChild(link);
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

  function init(textarea, CK, Premium) {
    if (textarea.dataset.ckeditorInitialized === "true") return;
    textarea.dataset.ckeditorInitialized = "true";
    textarea.classList.add("nv-ckeditor-source");
    const host = document.createElement("div");
    host.className = "nv-ckeditor-host";
    textarea.insertAdjacentElement("afterend", host);
    const initialValue = textarea.value || "";
    const form = textarea.form;
    const config = {
      licenseKey: "eyJhbGciOiJFUzI1NiJ9.eyJleHAiOjE3OTQwOTU5OTksImp0aSI6IjY5ZTM2ZjlkLThjYmQtNGZmZC1hM2VlLWJkY2I4YWVhYTE1OSIsInVzYWdlRW5kcG9pbnQiOiJodHRwczovL3Byb3h5LWV2ZW50LmNrZWRpdG9yLmNvbSIsImRpc3RyaWJ1dGlvbkNoYW5uZWwiOlsiY2xvdWQiLCJkcnVwYWwiLCJzaCJdLCJ3aGl0ZUxhYmVsIjp0cnVlLCJsaWNlbnNlVHlwZSI6InRyaWFsIiwiZmVhdHVyZXMiOlsiKiJdLCJ2YyI6ImE4N2NiZTJlIn0.DkPmttkEjTz41CkQ1JQVMUwt91_xbIYqilw_Sngcl3b9smAgzvYsnuL7vHvFBJi9pUYdoSDlh5Exxr5KaPrp4A",
      placeholder: textarea.getAttribute("placeholder") || "Type or paste your content here…",
      plugins: [
        CK.Alignment, CK.Autoformat, CK.AutoImage, CK.AutoLink, CK.Autosave, CK.BalloonToolbar,
        CK.BlockQuote, CK.Bold, CK.Bookmark, Premium.CaseChange, CK.Code, CK.CodeBlock,
        CK.Essentials, Premium.ExportInlineStyles, Premium.ExportPdf, Premium.ExportWord,
        CK.FindAndReplace, CK.FontBackgroundColor, CK.FontColor, CK.FontFamily, CK.FontSize,
        Premium.Footnotes, Premium.FormatPainter, CK.Fullscreen, CK.GeneralHtmlSupport,
        CK.Heading, CK.Highlight, CK.HorizontalLine, CK.HtmlEmbed, CK.ImageBlock, CK.ImageCaption,
        CK.ImageEditing, CK.ImageInline, CK.ImageInsert, CK.ImageInsertViaUrl, CK.ImageResize,
        CK.ImageStyle, CK.ImageTextAlternative, CK.ImageToolbar, CK.ImageUpload, CK.ImageUtils,
        Premium.ImportWord, CK.Indent, CK.IndentBlock, CK.Italic, Premium.LineHeight, CK.Link,
        CK.LinkImage, CK.List, CK.ListProperties, CK.MediaEmbed, Premium.MultiLevelList, CK.PageBreak,
        CK.Paragraph, CK.PasteFromOffice, Premium.PasteFromOfficeEnhanced, CK.PictureEditing,
        CK.PlainTableOutput, CK.RemoveFormat, CK.ShowBlocks, CK.SlashCommand, CK.SpecialCharacters,
        CK.SpecialCharactersArrows, CK.SpecialCharactersCurrency, CK.SpecialCharactersEssentials,
        CK.SpecialCharactersLatin, CK.SpecialCharactersMathematical, CK.SpecialCharactersText,
        CK.Strikethrough, CK.Subscript, CK.Superscript, CK.Table, CK.TableCaption,
        CK.TableCellProperties, CK.TableColumnResize, CK.TableLayout, Premium.TableOfContents,
        CK.TableProperties, CK.TableToolbar, Premium.Template, CK.TextPartLanguage,
        CK.TextTransformation, CK.TodoList, Premium.TrackChanges, Premium.TrackChangesData,
        Premium.TrackChangesPreview, CK.Underline, CK.WordCount
      ],
      extraPlugins: [NebulaUploadAdapterPlugin],
      toolbar: {
        items: [
          "undo", "redo", "|", "importWord", "exportWord", "exportPdf", "showBlocks",
          "formatPainter", "caseChange", "findAndReplace", "textPartLanguage", "fullscreen",
          "|", "heading", "|", "fontSize", "fontFamily", "fontColor", "fontBackgroundColor",
          "|", "bold", "italic", "underline", "strikethrough", "subscript", "superscript",
          "code", "removeFormat", "|", "specialCharacters", "horizontalLine", "pageBreak",
          "link", "insertFootnote", "bookmark", "insertImage", "insertImageViaUrl", "mediaEmbed",
          "insertTable", "insertTableLayout", "tableOfContents", "insertTemplate", "highlight",
          "blockQuote", "codeBlock", "htmlEmbed", "|", "alignment", "lineHeight", "|",
          "bulletedList", "numberedList", "multiLevelList", "todoList", "outdent", "indent"
        ],
        shouldNotGroupWhenFull: false
      },
      balloonToolbar: ["bold", "italic", "|", "link", "insertImage", "|", "bulletedList", "numberedList"],
      menuBar: { isVisible: true },
      autosave: {
        save: editor => { textarea.value = editor.getData(); return Promise.resolve(); },
        waitingTime: 1500
      },
      alignment: { options: ["left", "center", "right", "justify"] },
      fontFamily: { supportAllValues: true },
      fontSize: { options: [10, 12, 14, "default", 18, 20, 22], supportAllValues: true },
      lineHeight: { supportAllValues: true },
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
      exportInlineStyles: { stylesheets: [CORE_CSS, PREMIUM_CSS] },
      exportPdf: {
        stylesheets: [CORE_CSS, PREMIUM_CSS], fileName: "nebula-vault-document.pdf",
        converterOptions: { format: "A4", margin_top: "20mm", margin_bottom: "20mm",
          margin_right: "20mm", margin_left: "20mm", page_orientation: "portrait" }
      },
      exportWord: {
        stylesheets: [CORE_CSS, PREMIUM_CSS], fileName: "nebula-vault-document.docx",
        converterOptions: { document: { orientation: "portrait", size: "A4",
          margins: { top: "20mm", bottom: "20mm", right: "20mm", left: "20mm" } } }
      },
      link: {
        addTargetToExternalLinks: true, defaultProtocol: "https://",
        decorators: { toggleDownloadable: { mode: "manual", label: "Downloadable", attributes: { download: "file" } } }
      },
      list: { properties: { styles: true, startIndex: true, reversed: true } },
      table: { contentToolbar: ["tableColumn", "tableRow", "mergeTableCells", "tableProperties", "tableCellProperties"] },
      template: { definitions: [] },
      initialData: initialValue
    };

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

  function start() {
    const fields = [...document.querySelectorAll(ELIGIBLE)].filter(el => !el.matches(EXCLUDED));
    if (!fields.length) return;
    addStylesheet(CORE_CSS);
    addStylesheet(PREMIUM_CSS);
    const core = document.createElement("script");
    core.src = "https://cdn.ckeditor.com/ckeditor5/" + VERSION + "/ckeditor5.umd.js";
    core.crossOrigin = "anonymous";
    core.onload = () => {
      const premium = document.createElement("script");
      premium.src = "https://cdn.ckeditor.com/ckeditor5-premium-features/" + VERSION + "/ckeditor5-premium-features.umd.js";
      premium.crossOrigin = "anonymous";
      premium.onload = () => fields.forEach(field => init(field, window.CKEDITOR || {}, window.CKEDITOR_PREMIUM_FEATURES || {}));
      premium.onerror = () => console.error("Unable to load CKEditor premium features.");
      document.head.appendChild(premium);
    };
    core.onerror = () => console.error("Unable to load CKEditor 5 from the configured CDN.");
    document.head.appendChild(core);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();