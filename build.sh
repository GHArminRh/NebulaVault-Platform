#!/usr/bin/env bash
set -euo pipefail

# ParsPack installs requirements.txt during its managed dependency-install stage
# before this custom build command runs. Do not install them a second time here.

# Verify that browser-facing CSS bundles were generated from the reviewed source modules.
python scripts/build_frontend_css.py --check

# Keep database migrations out of the image build. start_parspack.sh invokes
# render_startup against the ParsPack-specific DATABASE_URL at runtime.
python manage.py collectstatic --noinput
