#!/bin/bash
# dayone_attach.sh — inserts weekly Conditions map images into a Day One entry via
# clipboard paste. The Day One CLI's --attachments import is broken (records a moment
# but never embeds bytes → blank placeholder). Pasting image data via System Events
# creates a real, syncing photo moment identical to using the GUI "+" button.
#
# REQUIRES: two macOS grants for the host app — Accessibility (System Settings →
# Privacy & Security → Accessibility) AND Automation for Apple Events to System
# Events / Day One. Without them System Events keystrokes are blocked and paste
# silently fails. Both were verified present on 2026-07-31, so treat a failed
# paste as a focus/timing problem first, not a permissions problem; confirm with
#   osascript -e 'tell application "System Events" to return name of first application process'
# which returns a process name when Automation is granted.
#
# Subcommands:
#   list                          Print this run's Conditions map PNGs, in insert order. Only maps
#                                 stamped with today's date qualify (override via FISHING_MAP_STAMP);
#                                 anything missing prints MISSING:<file> to stderr and is skipped, so
#                                 a stale render is never embedded in a fresh report.
#   count <ENTRY_UUID>            Print the number of embedded photos (ZHASDATA=1) on the entry.
#   paste <ENTRY_UUID> <IMG>      Open entry, move cursor to end, load IMG to clipboard, paste
#                                 via System Events, wait for embed. Prints "PASTED=<new_count>".
#                                 Use for the FIRST map — opens/focuses the entry.
#   clip_paste <ENTRY_UUID> <IMG> Load IMG to clipboard and paste via System Events WITHOUT
#                                 reopening the entry (preserves edit focus). Prints "PASTED=<new_count>".
#                                 Use for maps 2..N.
#
#   -- Legacy subcommands (kept for backward compat) --
#   stage <ENTRY_UUID> <IMG>      Open entry + load clipboard only. Prints "BASELINE=<n>". No paste.
#   clip <IMG>                    Load clipboard only. No paste.
#
# Fully automated usage (no computer-use needed — call via mcp__Control_your_Mac__osascript):
#   bash tools/dayone_attach.sh paste      "$UUID" "$MAP1"
#   bash tools/dayone_attach.sh clip_paste "$UUID" "$MAP2"
#   bash tools/dayone_attach.sh clip_paste "$UUID" "$MAP3"
#   bash tools/dayone_attach.sh clip_paste "$UUID" "$MAP4"
#   bash tools/dayone_attach.sh count "$UUID"   # verify == 4

set -euo pipefail

PROJECT_DIR="${FISHING_PROJECT_DIR:-/Users/edmatibag/Documents/Claude/Projects/Weekly Saltwater Fishing Report}"
MAPS_DIR="$PROJECT_DIR/conditions_maps"
DB="$HOME/Library/Group Containers/5U8NS4GX82.dayoneapp2/Data/Documents/DayOne.sqlite"

# Insert order: SoCal temp-break, SoCal water-color, Baja temp-break, Baja water-color.
MAP_KEYS=(socal_temp_break socal_water_color baja_temp_break baja_water_color)

# Only maps rendered for THIS run are eligible. Override for a backfill/replay.
STAMP="${FISHING_MAP_STAMP:-$(date +%Y%m%d)}"

map_for_stamp() {
  # PNG for the given key at STAMP only.
  #
  # This used to be `ls -t "$MAPS_DIR/$1"_*.png | head -1` (newest match, any date), which
  # silently returned a WEEKS-OLD render whenever a map source failed for the current run —
  # e.g. on 2026-07-31 the chlorophyll dataset 404'd and `list` happily offered the
  # 2026-07-14 water-color maps for embedding, which would have put stale water colour in a
  # report dated two weeks later. Never fall back to an older render: a missing map must
  # stay missing so the caller embeds only what was actually produced this week.
  local f="$MAPS_DIR/$1_$STAMP.png"
  [ -f "$f" ] && echo "$f"
  # Always succeed: under `set -e` a failing command substitution in an assignment aborts
  # the caller, which would make `list` exit silently on the first absent map.
  return 0
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
      f="$(map_for_stamp "$k")"
      [ -n "$f" ] && echo "$f" || echo "MISSING:${k}_${STAMP}.png" >&2
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
  paste)
    # Open entry, load image to clipboard, paste via System Events — no computer-use needed.
    uuid="${2:?entry uuid required}"
    img="${3:?image path required}"
    [ -f "$img" ] || { echo "ERROR: image not found: $img" >&2; exit 1; }
    open -a "Day One" 2>/dev/null || true
    sleep 1
    open "dayone://edit?entryId=$uuid"
    sleep 3
    osascript -e "set the clipboard to (read (POSIX file \"$img\") as «class PNGf»)"
    sleep 0.5
    osascript -e 'tell application "System Events" to tell process "Day One" to keystroke "v" using command down'
    sleep 4
    echo "PASTED=$(embedded_count "$uuid")"
    ;;
  clip_paste)
    # Load image to clipboard and paste via System Events — does NOT reopen the entry.
    # Use for maps 2..N while Day One editor is already focused on the entry.
    uuid="${2:?entry uuid required}"
    img="${3:?image path required}"
    [ -f "$img" ] || { echo "ERROR: image not found: $img" >&2; exit 1; }
    osascript -e "set the clipboard to (read (POSIX file \"$img\") as «class PNGf»)"
    sleep 0.5
    osascript -e 'tell application "System Events" to tell process "Day One" to keystroke "v" using command down'
    sleep 4
    echo "PASTED=$(embedded_count "$uuid")"
    ;;
  stage)
    # Legacy: open entry + load clipboard. Caller must send Cmd+V externally.
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
    echo "usage: $0 {list|count <uuid>|paste <uuid> <img>|clip_paste <uuid> <img>|stage <uuid> <img>|clip <img>}" >&2
    exit 2
    ;;
esac
