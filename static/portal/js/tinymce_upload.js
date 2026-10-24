/* CSRF-safe image upload adapter for django-tinymce's bundled editor. */
(function () {
  "use strict";

  function readCookie(name) {
    const prefix = name + "=";
    const entry = document.cookie.split(";").map((item) => item.trim())
      .find((item) => item.startsWith(prefix));
    return entry ? decodeURIComponent(entry.slice(prefix.length)) : "";
  }

  function uploadImage(blobInfo, progress) {
    return new Promise((resolve, reject) => {
      const request = new XMLHttpRequest();
      request.open("POST", "/admin/editor-upload/");
      request.withCredentials = true;

      const token = readCookie("csrftoken") ||
        (document.querySelector('input[name="csrfmiddlewaretoken"]') || {}).value || "";
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

  function installUploadAdapter() {
    if (!window.tinymce || window.tinymce.__nebulaUploadAdapterInstalled) return;

    const originalInit = window.tinymce.init.bind(window.tinymce);
    window.tinymce.init = function (options) {
      const config = Object.assign({}, options || {});
      if (!config.images_upload_handler) config.images_upload_handler = uploadImage;
      return originalInit(config);
    };
    window.tinymce.__nebulaUploadAdapterInstalled = true;
  }

  /*
   * This script is loaded after tinymce.min.js and before init_tinymce.js.
   * Install synchronously: waiting for DOMContentLoaded lets the initializer
   * run first, so the editor misses our images_upload_handler.
   */
  installUploadAdapter();
})();
