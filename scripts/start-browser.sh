#!/bin/bash

sleep 5

/usr/bin/chromium \
  --start-fullscreen \
  --no-first-run \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  --hide-crash-restore-bubble \
  --disable-infobars \
  --disable-features=TranslateUI \
  --password-store=basic \
  --remote-debugging-port=9222 \
  --noerrdialogs \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  about:blank
