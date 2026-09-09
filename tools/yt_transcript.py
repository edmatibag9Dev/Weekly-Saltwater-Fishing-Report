#!/usr/bin/python3
"""
yt_transcript.py — Chrome-free YouTube step for the Weekly Saltwater Fishing Report.

For each channel: read the channel's public Atom feed (exact ISO publish dates, no
"3 days ago" parsing), pick the newest upload inside the lookback window, confirm
captions exist, fetch the transcript with youtube_transcript_api, and write it to
  youtube_transcripts/<STAMP>/<key>.txt
plus a machine-readable manifest.json and a human summary on stdout.

Per-channel status values (manifest "status"):
  ok                 transcript written; "chars" = length
  no_new_video       nothing published inside --days
  no_captions        video exists but YouTube publishes no caption track (genuine; do not retry)
  fetch_failed       captions exist but the fetch failed -> FALL BACK TO THE CHROME UI METHOD
                     ("error" carries the exception class; RequestBlocked / IpBlocked means
                     YouTube is rate-limiting this IP, not a bug in this script)
  feed_failed        the channel feed itself could not be read -> fall back to Chrome listing

Run with /usr/bin/python3 explicitly. Under launchd PATH is /bin:/usr/bin:/usr/ucb:/usr/local/bin,
so a bare `python3` resolves to /usr/bin/python3 (3.9) — which is where the library lives.
The Homebrew python does NOT have it. Verified 2026-09-08 (youtube-transcript-api 1.2.4).
"""
import argparse, datetime as dt, json, os, re, shutil, sys, time, urllib.error, urllib.request
import xml.etree.ElementTree as ET

CHANNELS = [
    # key, display name, @handle, channel_id (resolved 2026-09-08; re-resolved at runtime if missing)
    ("bdoutdoors",         "BDoutdoors",                  "bdoutdoorsdotcom-m4p",       "UCyMghGNsPSHZ7DZdy1hJWHw"),
    ("friedman",           "Friedman Adventures Podcast", "FriedmanAdventuresPodcast",  "UCXgdKtE__ZDeFdXuASU-1Eg"),
    ("dancing_on_water",   "Dancing on Water",            "DancingonWater1203",         "UCwE6Ajn1nJGgy6DkEkM0vEg"),
    ("arthur_pereira",     "Arthur Pereira",              "ArthurPereira1974",          "UCfUDz5Z-afndDovNFQYnmnQ"),
    ("chasing_pelagics",   "Chasing Pelagics",            "ChasingPelagics",            "UCSLWuDeSNcsKCeDV6ci3R8Q"),
    ("fishermans_landing", "Fisherman's Landing",         "fishermanslanding",          "UCHQB-v-1mIN7IIW1FW4cHdg"),
]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
MIN_CHARS = 300          # below this a "transcript" is a Short/teaser — try the next candidate
PRUNE_DAYS = 56          # keep ~8 weeks of transcript folders, same policy as the maps

def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def resolve_channel_id(handle):
    html = http_get(f"https://www.youtube.com/@{handle}/videos")
    m = re.search(r'"externalId":"(UC[A-Za-z0-9_-]{22})"', html)
    return m.group(1) if m else None

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None

def is_short(video_id, attempts=2):
    """youtube.com/shorts/<id> answers 200 for a Short and 303 (redirect to /watch) for a normal
    video. The Atom feed does not flag Shorts and Fisherman's Landing posts several a week, so
    without this the newest 'upload' is often a 20-second clip with no captions. Verified 2026-09-08
    (3/3 consistent on four test videos; oEmbed dimensions are NOT usable — every video reports
    200x113). Returns None only if the probe errors twice; the caller then treats the video as
    normal and records a warning, because dropping a real report is worse than probing a Short."""
    req = urllib.request.Request(f"https://www.youtube.com/shorts/{video_id}", method="HEAD",
                                 headers={"User-Agent": UA})
    for i in range(attempts):
        try:
            urllib.request.build_opener(_NoRedirect).open(req, timeout=20)
            return True                      # 200 = it really is a Short
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                return False
            # 4xx/5xx: not a redirect, not a page — inconclusive; retry once
        except Exception:
            pass
        time.sleep(2 * (i + 1))
    return None

def feed_entries(channel_id):
    xml = http_get(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}")
    root = ET.fromstring(xml)
    out = []
    for e in root.findall("a:entry", NS):
        out.append({
            "video_id": e.find("yt:videoId", NS).text,
            "title": (e.find("a:title", NS).text or "").strip(),
            "published": e.find("a:published", NS).text,
        })
    return out

def pick_transcript(tlist):
    """Prefer a manual English track, then auto-generated English, then any en-*, then translate."""
    tr = list(tlist)
    for pred in (lambda t: t.language_code == "en" and not t.is_generated,
                 lambda t: t.language_code == "en" and t.is_generated,
                 lambda t: t.language_code.startswith("en")):
        for t in tr:
            if pred(t):
                return t, None
    for t in tr:
        if getattr(t, "is_translatable", False):
            return t.translate("en"), f"translated from {t.language_code}"
    return (tr[0], f"non-English track {tr[0].language_code}") if tr else (None, None)

BLOCKED = None   # set to the error string the first time YouTube blocks this IP in a run

def _first_line(e):
    return next((l.strip() for l in str(e).splitlines() if l.strip()), "")[:160]

def fetch_transcript(video_id, attempts=3):
    global BLOCKED
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled
    if BLOCKED:
        return {"status": "fetch_failed", "error": f"not attempted — {BLOCKED}"}
    last = None
    for i in range(attempts):
        try:
            api = YouTubeTranscriptApi()
            tlist = api.list(video_id)
            t, note = pick_transcript(tlist)
            if t is None:
                return {"status": "no_captions"}
            segs = t.fetch()
            text = re.sub(r"\s+", " ", " ".join(s.text for s in segs)).strip()
            return {"status": "ok", "text": text, "chars": len(text),
                    "track": f"{t.language_code}{' (auto)' if t.is_generated else ''}", "note": note}
        except (NoTranscriptFound, TranscriptsDisabled):
            return {"status": "no_captions"}
        except Exception as e:                      # RequestBlocked, IpBlocked, YouTubeRequestFailed, network...
            last = f"{type(e).__name__}: {_first_line(e)}"
            if type(e).__name__ in ("IpBlocked", "RequestBlocked"):
                # Retrying only deepens the block. Stop fetching for the rest of the run; the
                # feed listing + Shorts probe still run so every FETCH_FAILED line carries a URL
                # for the Chrome fallback. Hit for real on 2026-09-08 after ~20 fetches in 10 min.
                BLOCKED = f"YouTube {type(e).__name__} this IP earlier in the run"
                return {"status": "fetch_failed", "error": last}
            time.sleep(3 * (i + 1))
    return {"status": "fetch_failed", "error": last}

def drop_stale(outdir, key, rec):
    """An earlier run today may have written <key>.txt; if this run's status for the channel is
    not OK, that file must not survive to masquerade as this run's transcript."""
    stale = os.path.join(outdir, f"{key}.txt")
    if os.path.exists(stale):
        os.remove(stale)
        rec["removed_stale_file"] = True

def prune(base, days):
    cutoff = time.time() - days * 86400
    for d in os.listdir(base) if os.path.isdir(base) else []:
        p = os.path.join(base, d)
        if os.path.isdir(p) and re.fullmatch(r"\d{8}", d) and os.path.getmtime(p) < cutoff:
            shutil.rmtree(p, ignore_errors=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "youtube_transcripts"))
    ap.add_argument("--stamp", default=dt.date.today().strftime("%Y%m%d"))
    ap.add_argument("--only", help="comma-separated channel keys to run")
    args = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    window = now - dt.timedelta(days=args.days)
    outdir = os.path.abspath(os.path.join(args.out, args.stamp))
    os.makedirs(outdir, exist_ok=True)
    prune(os.path.abspath(args.out), PRUNE_DAYS)

    manifest = {"stamp": args.stamp, "generated": now.isoformat(timespec="seconds"), "days": args.days, "channels": []}
    only = set(args.only.split(",")) if args.only else None

    for key, name, handle, cid in CHANNELS:
        if only and key not in only:
            continue
        rec = {"key": key, "name": name, "handle": handle, "channel_id": cid}
        try:
            if not cid:
                cid = resolve_channel_id(handle); rec["channel_id"] = cid
            entries = feed_entries(cid)
        except Exception as e:
            rec.update(status="feed_failed", error=f"{type(e).__name__}: {str(e)[:160]}")
            drop_stale(outdir, key, rec); manifest["channels"].append(rec); continue

        cands = [x for x in entries if dt.datetime.fromisoformat(x["published"].replace("Z", "+00:00")) >= window]
        cands.sort(key=lambda x: x["published"], reverse=True)
        if not cands:
            newest = entries[0]["published"][:10] if entries else "none"
            rec.update(status="no_new_video", newest_upload=newest)
            drop_stale(outdir, key, rec); manifest["channels"].append(rec); continue

        rec["skipped"] = []
        chosen = None
        last_res = None
        for c in cands:
            sc = None if re.search(r"#shorts?\b", c["title"], re.I) else is_short(c["video_id"])
            if sc is True or (sc is None and re.search(r"#shorts?\b", c["title"], re.I)):
                rec["skipped"].append({**c, "why": "YouTube Short"}); continue
            if sc is None:
                rec.setdefault("warnings", []).append(
                    f"{c['video_id']}: Shorts probe inconclusive after 2 tries — treated as a normal video")
            res = fetch_transcript(c["video_id"])
            last_res = (c, res)
            if res["status"] == "no_captions":
                rec["skipped"].append({**c, "why": "no captions published"}); continue
            if res["status"] == "ok" and res["chars"] < MIN_CHARS and len(cands) > 1:
                rec["skipped"].append({**c, "why": f"transcript only {res['chars']} chars (teaser?)"}); continue
            chosen = (c, res); break

        if chosen is None:
            if last_res is None:
                # Nothing was even probed: every in-window upload was a Short. That is "no new
                # video", not "no captions" — say so, and name what was skipped.
                older = [x for x in entries if x not in cands]
                rec.update(status="no_new_video",
                           newest_upload=older[0]["published"][:10] if older else "none",
                           note=f"{len(cands)} in-window upload(s) were all Shorts")
                drop_stale(outdir, key, rec); manifest["channels"].append(rec); continue
            # Every real upload in the window was captionless / a teaser. Report the newest one
            # we actually probed so the status is honest (no_captions), not a bogus no_new_video.
            chosen = last_res
            rec["skipped"] = [x for x in rec["skipped"] if x["video_id"] != chosen[0]["video_id"]]

        c, res = chosen
        rec.update(video_id=c["video_id"], title=c["title"], published=c["published"],
                   url=f"https://www.youtube.com/watch?v={c['video_id']}", status=res["status"])
        if res["status"] == "ok":
            path = os.path.join(outdir, f"{key}.txt")
            with open(path, "w") as f:
                f.write(f"{name} — {c['title']}\n{rec['url']}\npublished {c['published']}  track {res['track']}"
                        f"{'  ' + res['note'] if res.get('note') else ''}\n\n{res['text']}\n")
            rec.update(chars=res["chars"], track=res["track"], path=path)
        elif res["status"] == "fetch_failed":
            rec["error"] = res["error"]
        if res["status"] != "ok":
            drop_stale(outdir, key, rec)
        manifest["channels"].append(rec)

    mpath = os.path.join(outdir, "manifest.json")
    if only and os.path.exists(mpath):
        # --only is a debugging aid: merge into today's manifest instead of clobbering the other channels
        try:
            prev = json.load(open(mpath))
            done = {c["key"] for c in manifest["channels"]}
            manifest["channels"] = [c for c in prev.get("channels", []) if c["key"] not in done] + manifest["channels"]
            manifest["channels"].sort(key=lambda c: [k for k, *_ in CHANNELS].index(c["key"]))
        except Exception:
            pass
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"# YouTube transcripts — {args.stamp} (window {args.days} d)  →  {outdir}")
    for r in manifest["channels"]:
        s = r["status"]
        if s == "ok":
            line = f"OK           {r['name']}: \"{r['title']}\" ({r['published'][:10]}, {r['chars']:,} chars, {r['track']}) → {os.path.basename(r['path'])}"
        elif s == "no_new_video":
            line = f"NO_NEW_VIDEO {r['name']}: newest upload {r['newest_upload']}" + (f" — {r['note']}" if r.get('note') else "")
        elif s == "no_captions":
            line = f"NO_CAPTIONS  {r['name']}: \"{r['title']}\" ({r['published'][:10]}) — transcript unavailable (no captions published)"
        elif s == "fetch_failed":
            line = f"FETCH_FAILED {r['name']}: \"{r['title']}\" {r['url']} — {r['error']}  ⇒ use Chrome fallback"
        else:
            line = f"FEED_FAILED  {r['name']}: {r.get('error')}  ⇒ use Chrome fallback (listing + transcript)"
        if r.get("warnings"):
            line += "  ⚠ " + "; ".join(r["warnings"])
        if r.get("skipped"):
            line += f"  [skipped {len(r['skipped'])} newer: " + "; ".join(f"{x['title'][:40]} ({x['why']})" for x in r["skipped"]) + "]"
        print(line)
    print(f"MANIFEST {mpath}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
