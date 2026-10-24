/* Nebula Vault rich-text editor initialization. */
(function () {
  "use strict";

  function parseConfig(textarea) {
    try {
      return JSON.parse(textarea.getAttribute("data-tinymce-config") || "{}");
    } catch (error) {
      console.error("Nebula editor: invalid editor configuration.", error);
      return {};
    }
  }

  function initialize() {
    if (!window.tinymce || typeof window.tinymce.init !== "function") {
      console.error("Nebula editor: TinyMCE runtime did not load.");
      return;
    }

    const fields = document.querySelectorAll("textarea[data-tinymce-config]");
    fields.forEach((textarea) => {
      if (textarea.dataset.nebulaEditorInitialized === "true") return;
      textarea.dataset.nebulaEditorInitialized = "true";

      const config = parseConfig(textarea);
      const options = Object.assign({}, config, {
        target: textarea,
        license_key: "gpl",
        setup: function (editor) {
          if (typeof config.setup === "function") config.setup(editor);
          editor.on("change input undo redo", function () {
            editor.save();
          });
        }
      });

      window.tinymce.init(options).catch((error) => {
        delete textarea.dataset.nebulaEditorInitialized;
        console.error("Nebula editor initialization failed.", error);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();
