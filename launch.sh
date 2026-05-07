#!/bin/bash
set -a
CONFIG="$HOME/.config/projmap/config"
[ -f "$CONFIG" ] && source "$CONFIG"
set +a
exec /home/ahrens/projmap/.venv/bin/projmap "$@"
