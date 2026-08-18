#!/bin/bash

set -e

URL="$1"
PROFILE="$2"
CDP_PORT="$3"

if [ -z "$URL" ] || [ -z "$PROFILE" ] || [ -z "$CDP_PORT" ]; then
    echo "Usage: $0 <url> <profile-dir> <cdp-port>"
    exit 1
fi

env DISPLAY=:0 \
    WAYLAND_DISPLAY=wayland-0 \
    XDG_RUNTIME_DIR=/run/user/1000 \
    DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
    XDG_SESSION_TYPE=wayland \
    /usr/bin/chromium \
    --user-data-dir="$PROFILE" \
    --remote-debugging-port="$CDP_PORT" \
    --no-first-run \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --noerrdialogs \
    --window-size=1920,1080 \
    --app="$URL"
