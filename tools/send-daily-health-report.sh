#!/bin/bash

set -u

RECIPIENT="joshua.thibeault@jamescitycountyva.gov"
SUBJECT="Station Dashboard Daily Health Report — $(date '+%b %-d, %Y')"

REPORT="$(/home/station1/station-dashboard/tools/analyze-daily-email.py 2>&1)"
STATUS=$?

{
    echo "To: ${RECIPIENT}"
    echo "From: jamescitybrutonvfd@gmail.com"
    echo "Subject: ${SUBJECT}"
    echo "Content-Type: text/plain; charset=UTF-8"
    echo
    echo "${REPORT}"
} | /usr/sbin/sendmail -t

exit $STATUS
