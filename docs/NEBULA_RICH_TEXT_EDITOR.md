# Nebula Vault rich-text editor

Nebula Vault now owns the Django-side rich-text integration in `nebula_editor/`.
The project no longer installs or registers the `django-tinymce` Django app.
Catalog forms use `NebulaTinyMCE`, the configuration lives in
`NEBULA_EDITOR_CONFIG`, and image uploads continue to use the authenticated,
staff-only `editor-image-upload` endpoint.

The TinyMCE browser runtime is pinned to version 7.8.0 and currently loaded from
jsDelivr. This means the Django integration is local to Nebula Vault, but the
editor runtime itself is still an upstream third-party asset and requires network
access in the browser. For a fully offline/self-hosted deployment, vendor the
official TinyMCE distribution (including its plugins, themes, skins, icons and
models) into `static/tinymce/`, then change the first entry in
`NebulaTinyMCE.Media.js` to `tinymce/tinymce.min.js`. Preserve TinyMCE's
license notices when redistributing the runtime.

To adjust the editor, edit `NEBULA_EDITOR_CONFIG` in `config/settings.py` or
the widget and initializer in `nebula_editor/` and `static/portal/js/`.
