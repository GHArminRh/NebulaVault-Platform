/* TinyMCE Cloud integration for Django staff content fields only. */
(function () {
  "use strict";

  const CONTENT_FIELDS = "textarea#id_description, textarea#id_release_notes";
  const UPLOAD_URL = "/admin/editor-upload/";

  function readCookie(name) {
    const prefix = name + "=";
    const entry = document.cookie.split(";").map((item) => item.trim())
      .find((item) => item.startsWith(prefix));
    return entry ? decodeURIComponent(entry.slice(prefix.length)) : "";
  }

  function csrfToken() {
    return readCookie("csrftoken") ||
      (document.querySelector('input[name="csrfmiddlewaretoken"]') || {}).value || "";
  }

  function uploadImage(blobInfo, progress) {
    return new Promise((resolve, reject) => {
      const request = new XMLHttpRequest();
      request.open("POST", UPLOAD_URL);
      request.withCredentials = true;

      const token = csrfToken();
      if (token) request.setRequestHeader("X-CSRFToken", token);

      request.upload.onprogress = (event) => {
        if (event.lengthComputable && typeof progress === "function") {
          progress((event.loaded / event.total) * 100);
        }
      };

      request.onload = () => {
        let result;
        try {
          result = JSON.parse(request.responseText);
        } catch (_) {
          reject("Image upload failed: the server returned an invalid response.");
          return;
        }

        if (request.status < 200 || request.status >= 300) {
          reject(result.error || "Image upload failed (HTTP " + request.status + ").");
          return;
        }
        const location = result.location || result.url;
        if (!location) {
          reject("Image upload failed: the server did not return an image URL.");
          return;
        }
        resolve(location);
      };

      request.onerror = () => reject("Image upload failed because of a network error.");

      const formData = new FormData();
      formData.append("file", blobInfo.blob(), blobInfo.filename());
      request.send(formData);
    });
  }

  function initializeContentEditors() {
    if (!window.tinymce || !document.querySelector(CONTENT_FIELDS)) return;

    window.tinymce.init({
      selector: CONTENT_FIELDS,
      menubar: false,
      branding: false,
      promotion: false,
      height: 420,
      resize: true,
      statusbar: true,
      plugins: "lists link image table code fullscreen",
      toolbar: [
        "undo redo | blocks | bold italic underline |",
        "alignleft aligncenter alignright | bullist numlist |",
        "link image table | removeformat | code fullscreen"
      ].join(" "),
      automatic_uploads: true,
      images_upload_handler: uploadImage,
      convert_urls: false,
      relative_urls: false,
      content_style: "body { font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; }",
      setup: function (editor) {
        editor.on("change input undo redo", function () {
          editor.save();
        });
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeContentEditors);
  } else {
    initializeContentEditors();
  }
})();
