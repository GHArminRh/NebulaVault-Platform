# Nebula Vault License Test Client

A small Windows-friendly desktop GUI to smoke-test the Django licensing endpoints. It uses only Python's standard library; no pip installation is required.

## Run

1. Start the Nebula Vault Django server.
2. In the admin panel, issue a license for a valid subscription and copy the plaintext key when it is shown.
3. Run `RUN_LICENSE_TEST_CLIENT.bat` (or `python app.py`).
4. Keep the default URL for a local development server: `http://127.0.0.1:8000`.
5. Paste the license key and test **Activate device**, **Validate license**, and **Deactivate device**.

## API requests sent

- `POST /api/licensing/activate/`
- `POST /api/licensing/validate/`
- `POST /api/licensing/deactivate/`

The client sends `license_key`, `device_fingerprint`, `device_name` (activate only is used by the API), and `app_version` as JSON. The fingerprint is a randomly generated UUID persisted in the current user's application-data folder so repeated launches simulate the same device.

The response panel displays the JSON body and HTTP status, including expected API rejections such as invalid keys or device limits.

## Notes

- Requires Python 3.10+ and a Python build that includes Tkinter (the standard Windows installer usually does).
- For a remote server, enter its base URL. Use HTTPS for any non-local deployment.
- This is a test utility, not the production Nebula Vault desktop client. It does not store the license key, and it does not replace server-side security or end-to-end testing.
