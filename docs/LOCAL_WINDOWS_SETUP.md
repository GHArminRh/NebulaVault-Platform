# One-click local startup (Windows)

1. Install Python 3.11+ and PostgreSQL for Windows.
2. Download the repository ZIP for the `feat/nebula-platform-frontend` branch and extract it.
3. Double-click `START_NEBULA_VAULT.bat`.
4. On first run, enter the PostgreSQL administrator username/password when prompted. The launcher creates the local app role/database, writes a local-only `.env`, installs Python requirements, runs migrations, and opens the browser.
5. Keep the terminal window open while using the site. Press Ctrl+C to stop the server.

The launcher is intended for local development only. It binds to 127.0.0.1 and uses Django's development server. It does not configure production hosting or payment processing. Never share or commit your `.env` file. If PostgreSQL is installed under a custom port, update DB_PORT/DB_HOST in `.env` and adjust the setup script constants before first-time setup.
