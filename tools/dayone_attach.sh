#!/bin/bash
# dayone_attach.sh — verify (and, if needed, trigger) the import of this run's images into a
# Day One entry.
#
# HOW IMAGES GET INTO THE ENTRY (rewritten 2026-09-11 — read this before changing anything):
#   Day One on this Mac is the sandboxed App Store build. Its CLI / connector attachment import
#   reads the file lazily, the first time the entry is DISPLAYED, and it can only read files that
#   live inside the app's own group container. Two consequences, both verified on 2026-09-11:
#     1. Attach paths under /tmp, ~/Documents, or the project folder -> a moment is recorded but
#        the bytes are never imported ("blank placeholder"). Attach the SAME file from
#        ~/Library/Group Containers/5U8NS4GX82.dayoneapp2/Data/Documents/CLI-Inbox/ -> it imports.
#     2. The import happens when the entry is opened (`open "dayone://edit?entryId=<uuid>"`),
#        ~5 s later; a freshly created entry that nobody has opened shows ZHASDATA=0 until then.
#   So the run: conditions.py copies every produced image into CLI-Inbox and prints the ordered
#   list in its `<!-- ATTACHMENTS -->` footer; the Day One save passes that list as `attachments=`
#   (the text carries one `[{attachment}]` placeholder per image); then `trigger` opens the entry
#   and polls until the count matches. No keystrokes anywhere.
#
#   The former clipboard-paste path (`paste` / `clip_paste`) is DEAD: System Events keystrokes,
#   menu-driven Paste and even hardware-level CGEvent Cmd+V reach Day One but its editor ignores
#   them (tested 2026-09-11, screen unlocked, Day One frontmost, editor focused). It never once
#   embedded a map on a scheduled run (0 of 4 on every run from 2026-07-31 to 2026-09-11). The
#   subcommands are kept only so old transcripts still parse; they print a warning and exit 3.
#
# Subcommands:
#   inbox                         Print this run's attachment list (the CLI-Inbox paths, in insert
#                                 order) from conditions_maps/attachments_<stamp>.txt. Empty if
#                                 conditions.py did not run today.
#   trigger <ENTRY_UUID> [N]      Open the entry in Day One to start the lazy import, then poll the
#                                 embedded-photo count every 3 s for up to 90 s until it reaches N
#                                 (default: the number of lines `inbox` prints). Prints
#                                 "EMBEDDED=<count>/<N>" and exits 0 when they match, 1 otherwise.
#   list                          Print this run's map PNGs in conditions_maps/ (project-folder
#                                 paths, today's stamp only; MISSING:<file> on stderr for absent
#                                 maps). Informational — attach the `inbox` paths, not these.
#   count <ENTRY_UUID>            Print the number of embedded photos (ZHASDATA=1) on the entry.
#                                 Prints "?" (not 0) if the DB can't be read — the read is
#                                 read-only, busy-timeout'd and hard-capped at
#                                 DAYONE_DB_TIMEOUT_SECS (default 8), so it can never hang.
#   paste | clip_paste | stage | clip   DEPRECATED (see above). Exit 3.
#
# Env: FISHING_PROJECT_DIR (project folder), FISHING_MAP_STAMP (YYYYMMDD, for replays),
#      DAYONE_DB_TIMEOUT_SECS.

set -euo pipefail

PROJECT_DIR="${FISHING_PROJECT_DIR:-/Users/edmatibag/Documents/Claude/Projects/Weekly Saltwater Fishing Report}"
MAPS_DIR="$PROJECT_DIR/conditions_maps"
DB="$HOME/Library/Group Containers/5U8NS4GX82.dayoneapp2/Data/Documents/DayOne.sqlite"

# Insert order: SoCal temp-break, SoCal water-color, Baja temp-break, Baja water-color, then the
# NHC 7-day outlook and any storm_<name> forecast cones (globbed, since storm names vary).
MAP_KEYS=(socal_temp_break socal_water_color baja_temp_break baja_water_color storm_outlook)

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

# Hard wall-clock cap for any DB read. macOS has no coreutils `timeout`, so roll one.
# Returns 124 on expiry, mirroring GNU timeout.
DB_TIMEOUT_SECS="${DAYONE_DB_TIMEOUT_SECS:-8}"

run_with_timeout() {
  local secs="$1"; shift
  "$@" &
  local pid=$! waited=0 limit=$(( secs * 10 ))
  while kill -0 "$pid" 2>/dev/null; do
    if [ "$waited" -ge "$limit" ]; then
      kill -TERM "$pid" 2>/dev/null || true
      sleep 0.5
      kill -KILL "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      return 124
    fi
    sleep 0.1
    waited=$(( waited + 1 ))
  done
  wait "$pid"
}

embedded_count() {
  # Counts embedded photos on an entry while Day One is running. This MUST NOT be able
  # to block: on 2026-08-07 the old one-liner hung indefinitely here and stalled the
  # whole PART 5 step — `paste` never returned even though its Cmd+V had already fired,
  # and the run had to be killed by hand.
  #
  # Why a snapshot copy rather than reading the live file:
  #   * The DB is WAL (a -wal and -shm sit next to it). Readers are not supposed to block
  #     writers in WAL — but opening a WAL database read-only still needs write access to
  #     the -shm, and in this sandbox that neither succeeds nor fails cleanly, it just
  #     stalls. `sqlite3 -readonly -cmd ".timeout 3000"` still timed out at 8s.
  #   * `file:$DB?immutable=1` does dodge the lock, but it ignores the -wal entirely, so a
  #     just-committed attachment is invisible and the caller reads a stale count — the
  #     worst possible failure mode when the whole point is verifying a paste landed.
  # Copying db + -wal + -shm to a scratch dir and querying the copy is lock-free, sees
  # WAL-resident commits, and cannot touch Day One's own files. ~45 MB, well under a second.
  #
  # On failure prints "?" (unknown), never a number. The old code did `|| echo 0`, which
  # reported an unreadable DB as "zero photos embedded" — indistinguishable from a real
  # empty entry, so a caller would retry a paste that had actually succeeded.
  local uuid="$1"
  case "$uuid" in
    ''|*[!0-9A-Fa-f-]*) echo "ERROR: bad entry uuid: $uuid" >&2; echo "?"; return 0 ;;
  esac

  local tmp out rc=0
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/dayone_count.XXXXXX")" || { echo "?"; return 0; }
  # shellcheck disable=SC2064
  trap "rm -rf '$tmp'" RETURN

  cp "$DB" "$tmp/db.sqlite" 2>/dev/null || { echo "WARN: cannot copy DB" >&2; echo "?"; return 0; }
  [ -f "$DB-wal" ] && cp "$DB-wal" "$tmp/db.sqlite-wal" 2>/dev/null || true
  [ -f "$DB-shm" ] && cp "$DB-shm" "$tmp/db.sqlite-shm" 2>/dev/null || true

  out="$(run_with_timeout "$DB_TIMEOUT_SECS" \
      sqlite3 -cmd ".timeout 3000" "$tmp/db.sqlite" \
      "SELECT COUNT(*) FROM ZENTRY e JOIN ZATTACHMENT a ON a.ZENTRY=e.Z_PK \
       WHERE e.ZUUID='$uuid' AND a.ZHASDATA=1;" 2>/dev/null)" || rc=$?

  if [ "$rc" -eq 124 ]; then
    echo "WARN: DB read timed out after ${DB_TIMEOUT_SECS}s" >&2
    echo "?"; return 0
  fi
  if [ "$rc" -ne 0 ] || [ -z "$out" ]; then
    echo "WARN: DB read failed (rc=$rc)" >&2
    echo "?"; return 0
  fi
  echo "$out"
}

cmd="${1:-}"
case "$cmd" in
  inbox)
    m="$MAPS_DIR/attachments_$STAMP.txt"
    [ -f "$m" ] && cat "$m"
    ;;
  trigger)
    uuid="${2:?entry uuid required}"
    m="$MAPS_DIR/attachments_$STAMP.txt"
    if [ -n "${3:-}" ]; then want="$3"; else want=$( [ -f "$m" ] && grep -c . "$m" || echo 0 ); fi
    if [ "$want" = "0" ]; then echo "EMBEDDED=0/0 (nothing to attach this run)"; exit 0; fi
    open -a "Day One" 2>/dev/null || true
    sleep 1
    open "dayone://edit?entryId=$uuid"
    have="?"
    for i in $(seq 1 30); do
      sleep 3
      have="$(embedded_count "$uuid")"
      if [ "$have" != "?" ] && [ "$have" -ge "$want" ] 2>/dev/null; then
        echo "EMBEDDED=$have/$want"; exit 0
      fi
    done
    echo "EMBEDDED=$have/$want"
    exit 1
    ;;
  list)
    for k in "${MAP_KEYS[@]}"; do
      f="$(map_for_stamp "$k")"
      [ -n "$f" ] && echo "$f" || echo "MISSING:${k}_${STAMP}.png" >&2
    done
    for f in "$MAPS_DIR"/storm_*_"$STAMP".png; do
      [ -f "$f" ] || continue
      case "$f" in *storm_outlook_*) continue ;; esac
      echo "$f"
    done
    ;;
  count)
    embedded_count "${2:?entry uuid required}"
    ;;
  paste|clip_paste|stage|clip)
    echo "DEPRECATED: '$cmd' used the clipboard-paste path, which Day One's editor ignores (2026-09-11)." >&2
    echo "Use: create the entry with attachments= from '$0 inbox', then '$0 trigger <uuid>'." >&2
    exit 3
    ;;
  *)
    echo "usage: $0 {inbox|trigger <uuid> [N]|list|count <uuid>}" >&2
    exit 2
    ;;
esac
