#!/bin/bash
# dayone_attach.sh — helper for inserting the weekly Conditions map images into a
# Day One entry via the clipboard-paste path (the Day One CLI's --attachments import
# is broken in this build: it records a moment but never embeds the bytes, leaving a
# blank placeholder. Pasting image data through the GUI creates a real, syncing moment).
#
# This script does only the DETERMINISTIC parts — it cannot send the Cmd+V keystroke
# itself (macOS blocks osascript System-Events keystrokes without an Accessibility
# grant). The caller (the Cowork agent) performs the paste via computer-use after
# `stage`, then calls `count` to verify.
#
# Subcommands:
#   list                       Print the 4 newest Conditions map PNGs, in insert order.
#   count <ENTRY_UUID>         Print the number of embedded photos (ZHASDATA=1) on the entry.
#   stage <ENTRY_UUID> <IMG>   Open the entry in edit mode + load IMG onto the clipboard,
#                              then print "BASELINE=<n>" (embedded-photo count before paste).
#                              Use for the FIRST map only — opening focuses the entry. The caller
#                              still must click into the body to enter edit mode before the paste.
#   clip <IMG>                 Load IMG onto the clipboard only — does NOT re-open the entry (which
#                              would reset edit mode). Use for maps 2..N while the editor stays focused.
#
# Usage in the job (per map):
#   base=$(dayone_attach.sh stage "$UUID" "$IMG" | sed -n 's/BASELINE=//p')
#   # -> computer-use: open_application "Day One"; key "cmd+v"; wait 3s
#   now=$(dayone_attach.sh count "$UUID")
#   # if now == base, retry the stage+paste once.

set -euo pipefail

PROJECT_DIR="${FISHING_PROJECT_DIR:-/Users/edmatibag/Documents/Claude/Projects/Weekly Saltwater Fishing Report}"
MAPS_DIR="$PROJECT_DIR/conditions_maps"
DB="$HOME/Library/Group Containers/5U8NS4GX82.dayoneapp2/Data/Documents/DayOne.sqlite"

# Insert order: SoCal temp-break, SoCal water-color, Baja temp-break, Baja water-color.
MAP_KEYS=(socal_temp_break socal_water_color baja_temp_break baja_water_color)

newest_map() {
  # newest PNG whose name starts with the given key
  ls -t "$MAPS_DIR/$1"_*.png 2>/dev/null | head -1
}

embedded_count() {
  local uuid="$1"
  sqlite3 "$DB" "SELECT COUNT(*) FROM ZENTRY e JOIN ZATTACHMENT a ON a.ZENTRY=e.Z_PK \
    WHERE e.ZUUID='$uuid' AND a.ZHASDATA=1;" 2>/dev/null || echo 0
}

cmd="${1:-}"
case "$cmd" in
  list)
    for k in "${MAP_KEYS[@]}"; do
      f="$(newest_map "$k")"
      [ -n "$f" ] && echo "$f" || echo "MISSING:$k" >&2
    done
    ;;
  count)
    embedded_count "${2:?entry uuid required}"
    ;;
  clip)
    img="${2:?image path required}"
    [ -f "$img" ] || { echo "ERROR: image not found: $img" >&2; exit 1; }
    osascript -e "set the clipboard to (read (POSIX file \"$img\") as «class PNGf»)"
    echo "CLIPPED=$(basename "$img")"
    ;;
  stage)
    uuid="${2:?entry uuid required}"
    img="${3:?image path required}"
    [ -f "$img" ] || { echo "ERROR: image not found: $img" >&2; exit 1; }
    base="$(embedded_count "$uuid")"
    open -a "Day One" 2>/dev/null || true
    sleep 1
    open "dayone://edit?entryId=$uuid"
    sleep 2
    osascript -e "set the clipboard to (read (POSIX file \"$img\") as «class PNGf»)"
    echo "BASELINE=$base"
    ;;
  *)
    echo "usage: $0 {list|count <uuid>|stage <uuid> <img>|clip <img>}" >&2
    exit 2
    ;;
esac
