#!/bin/zsh
# activate venv
source "$(dirname "$0")/../.venv/bin/activate"
# load .env into shell (safe simple KEY=VAL file)
set -a
[ -f "$(dirname "$0")/../.env" ] && source "$(dirname "$0")/../.env"
set +a
export PYTHONUNBUFFERED=1
uvicorn app.server:app --reload --host ${HOST:-127.0.0.1} --port ${PORT:-8765}
