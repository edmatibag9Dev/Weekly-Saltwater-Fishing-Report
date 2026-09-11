#!/usr/bin/env python3
"""
Weekly Conditions generator for the Saltwater Fishing Report.

Produces:
  1. A Markdown "Conditions" section printed to stdout (capture this into the report), including
     a Storm Watch block (named East Pacific tropical storms / hurricanes vs. the report regions)
     and `[{attachment}]` placeholders that position the images inline in the Day One entry.
  2. Map PNGs in ./conditions_maps/ (temp-break, water-color, NHC 7-day outlook, NHC forecast cones).
  3. A PDF briefing in ./conditions_briefings/ (region tables, maps, Storm Watch).
  4. Copies of every produced image in Day One's sandbox-readable inbox
     (~/Library/Group Containers/5U8NS4GX82.dayoneapp2/Data/Documents/CLI-Inbox/) plus an ordered
     manifest, so the run can pass them as `attachments=` when it creates the entry.

Data sources (no Chrome, no login required):
  - Wind / swell / SST numbers ....... Open-Meteo Marine + Weather APIs
  - Temperature-break maps ........... NOAA MUR 1 km SST via NOAA CoastWatch ERDDAP
  - Water-color maps ................. DINEOF gap-filled chlorophyll via NOAA CoastWatch ERDDAP
  - Storm Watch ...................... NOAA National Hurricane Center (CurrentStorms.json, the
                                       TCM forecast/advisory text, the TWO outlook text + graphic)
  - Moon phase ....................... ephem (falls back to an approximation)

Safe to re-run. Degrades gracefully: if the map server is unavailable the text
still prints and the maps are reported as unavailable.

Run deps once per environment:
  pip install matplotlib numpy ephem --break-system-packages -q
"""
import os, sys, math, csv, io, json, re, glob, time, datetime, urllib.request, urllib.error

# macOS path to this project (used for the Day One attachment paths the run passes
# to the Day One MCP). The script itself writes to the sandbox-mounted equivalent.
PROJECT_MAC = os.environ.get(
    "FISHING_PROJECT_MAC",
    "/Users/edmatibag/Documents/Claude/Projects/Weekly Saltwater Fishing Report")
HERE = os.path.dirname(os.path.abspath(__file__))
MAPS_DIR = os.path.join(HERE, "conditions_maps")
BRIEF_DIR = os.path.join(HERE, "conditions_briefings")
os.makedirs(MAPS_DIR, exist_ok=True)
os.makedirs(BRIEF_DIR, exist_ok=True)

# Day One is the sandboxed App Store build. Its CLI/connector attachment import can only read
# files that live inside the app's own group container -- anything under /tmp or ~/Documents is
# silently skipped, which is what produced "blank placeholder" attachments for months. Every image
# this script produces is therefore also copied here, and the run attaches THESE paths.
# Override with DAYONE_INBOX (e.g. when testing on another Mac). If the container does not exist
# the copy step is skipped and no placeholders are emitted.
DAYONE_INBOX = os.environ.get(
    "DAYONE_INBOX",
    os.path.expanduser("~/Library/Group Containers/5U8NS4GX82.dayoneapp2/Data/Documents/CLI-Inbox"))

def _plain(s):
    """Strip markdown bold/italic and emoji for PDF text (reportlab core fonts lack emoji glyphs)."""
    s = s.replace("**", "").replace("_", "")
    return "".join(c for c in s if ord(c) < 0x2600).strip()

def prune_old(days=56):
    """Delete map/briefing files older than ~8 weeks so the folders don't grow forever."""
    cutoff = datetime.datetime.now().timestamp() - days * 86400
    for d in (MAPS_DIR, BRIEF_DIR, DAYONE_INBOX):
        if not os.path.isdir(d):
            continue
        for f in glob.glob(os.path.join(d, "*")):
            try:
                if os.path.isfile(f) and os.path.getmtime(f) < cutoff:
                    os.remove(f)
            except OSError:
                pass

# DINEOF gap-filled chlorophyll. Gap-filled = clean single-frame coverage (clouds interpolated).
# Tried in order; the first dataset that answers wins, and its label is printed on the map footer
# so the rendered lag is always visible rather than assumed.
#
# NOTE 2026-07-31: the former 2 km dataset "noaacwNPPN20S3ASCIDINEOF2kmDaily" was retired by NOAA
# CoastWatch and now returns HTTP 404 — that outage is what silently dropped both water-color maps
# from the 2026-07-31 run. The surviving DINEOF products are 9 km. Near-real-time leads with a ~2-day
# lag (what a forward-looking weekly briefing actually wants); the science-quality products run
# ~11-12 days behind and serve as backstops.
CHL_DATASETS = [
    ("noaacwNPPN20VIIRSDINEOFDaily",    "VIIRS SNPP+NOAA-20 · DINEOF gap-filled · near-real-time 9 km"),
    ("noaacwNPPN20S3ASCIDINEOFDaily",   "VIIRS SNPP+NOAA-20 + Sentinel-3A OLCI · DINEOF gap-filled · science 9 km"),
    ("noaacwNPPN20VIIRSSCIDINEOFDaily", "VIIRS SNPP+NOAA-20 · DINEOF gap-filled · science 9 km"),
]
_UA = {"User-Agent": "Mozilla/5.0 (conditions.py fishing-report)"}

def _urlopen(url, timeout=30, attempts=4):
    """Fetch with backoff on transient failures.

    NOAA's ERDDAP servers return sporadic 503s under load — observed ~25% of calls on
    coastwatch.pfeg.noaa.gov (which is the only host serving jplMURSST41; the newer
    coastwatch.noaa.gov 404s for it, so a mirror is not an option). A single 503 used to
    silently drop one map from the run, so retry rather than give up on the first miss.
    4xx other than 429 are permanent — fail fast on those instead of burning the backoff.
    """
    delay = 2.0
    for i in range(attempts):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=_UA), timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 429:
                raise
            if i == attempts - 1:
                raise
        except Exception:
            if i == attempts - 1:
                raise
        time.sleep(delay)
        delay *= 2

TODAY = datetime.date.today()
WEEK_END = TODAY + datetime.timedelta(days=6)

# name, lat, lon, tier  (representative point per region)
REGIONS = [
    ("Southern California Bight", 32.9, -117.8, "core"),
    ("Northern Baja",            31.6, -116.9, "core"),
    ("San Clemente & Catalina",  33.1, -118.5, "core"),
    ("Tanner / Cortez Banks",    32.5, -119.2, "bank"),
    ("Cedros / Guadalupe",       28.2, -115.2, "bank"),
    ("Magdalena Bay",            24.4, -112.2, "bank"),
    ("The Ridge",                25.3, -114.6, "bank"),
    ("Alijos Rocks",             24.95, -115.73, "bank"),
]

_DIRS = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
def compass(d): return _DIRS[int((d/22.5)+0.5) % 16]
def circ_mean(degs):
    s = sum(math.sin(math.radians(d)) for d in degs)
    c = sum(math.cos(math.radians(d)) for d in degs)
    return math.degrees(math.atan2(s, c)) % 360
def _get(url):
    with _urlopen(url, 30) as r:
        return json.load(r)

def fetch_region(lat, lon):
    m = _get(f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}"
             "&daily=swell_wave_height_max,swell_wave_period_max,wave_direction_dominant,"
             "sea_surface_temperature_max,sea_surface_temperature_min"
             "&timezone=America/Los_Angeles&forecast_days=7&length_unit=imperial&temperature_unit=fahrenheit")["daily"]
    w = _get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
             "&daily=wind_speed_10m_max,wind_gusts_10m_max,wind_direction_10m_dominant"
             "&timezone=America/Los_Angeles&forecast_days=7&wind_speed_unit=kn")["daily"]
    nn = lambda k, d: [x for x in d[k] if x is not None]
    return {
        "wind":  f"{compass(circ_mean(w['wind_direction_10m_dominant']))} "
                 f"{round(min(nn('wind_speed_10m_max',w)))}–{round(max(nn('wind_speed_10m_max',w)))} kt, "
                 f"gusts {round(max(nn('wind_gusts_10m_max',w)))}",
        "swell": f"{round(min(nn('swell_wave_height_max',m)),1)}–{round(max(nn('swell_wave_height_max',m)),1)} ft "
                 f"{compass(circ_mean(m['wave_direction_dominant']))} @ "
                 f"{round(min(nn('swell_wave_period_max',m)))}–{round(max(nn('swell_wave_period_max',m)))}s",
        "sst":   f"{round(min(nn('sea_surface_temperature_min',m)))}–"
                 f"{round(max(nn('sea_surface_temperature_max',m)))}°F",
    }

def moon_line():
    try:
        import ephem
        illum = []
        for i in range(7):
            d = TODAY + datetime.timedelta(days=i)
            illum.append(round(ephem.Moon(d.strftime("%Y/%m/%d")).phase))
        start = TODAY.strftime("%Y/%m/%d")
        nf = ephem.localtime(ephem.next_full_moon(start)).date()
        nn = ephem.localtime(ephem.next_new_moon(start)).date()
        events = []
        if TODAY <= nf <= WEEK_END: events.append(("Full Moon \U0001F315", nf))
        if TODAY <= nn <= WEEK_END: events.append(("New Moon \U0001F311", nn))
        lo, hi = min(illum), max(illum)
        waxing = illum[-1] >= illum[0]
        ev = "; ".join(f"{n} {d.strftime('%b %-d')}" for n, d in events) if events else \
             (f"{'Waxing' if waxing else 'Waning'} {'Gibbous' if hi>50 else 'Crescent'}")
        if hi >= 80:
            note = "Big bright nights — expect a tougher midday bite and the better window at grey light (dawn/dusk)."
        elif lo <= 20:
            note = "Dark nights — generally a stronger daytime bite this week."
        else:
            note = "Moderate moon — no major lunar handicap on the daytime bite."
        return f"\U0001F319 **Moon:** {ev} · {lo}–{hi}% illuminated this week. {note}"
    except Exception as e:
        return f"\U0001F319 **Moon:** (unavailable: {e})"

# ---------------- maps ----------------
def fetch_mur(lat0, lat1, lon0, lon1, stride):
    u = ("https://coastwatch.pfeg.noaa.gov/erddap/griddap/jplMURSST41.csv?analysed_sst"
         f"%5B(last)%5D%5B({lat0}):{stride}:({lat1})%5D%5B({lon0}):{stride}:({lon1})%5D")
    raw = _urlopen(u, 42).read().decode()
    rows = list(csv.reader(io.StringIO(raw)))[2:]
    import numpy as np
    lats = sorted(set(float(r[1]) for r in rows)); lons = sorted(set(float(r[2]) for r in rows))
    li = {v: i for i, v in enumerate(lats)}; lo = {v: i for i, v in enumerate(lons)}
    g = np.full((len(lats), len(lons)), np.nan)
    date = rows[0][0][:10]
    for r in rows:
        v = r[3]
        if v not in ("", "NaN"):
            g[li[float(r[1])], lo[float(r[2])]] = float(v) * 9 / 5 + 32
    return lats, lons, g, date

def _fetch_chl_one(ds, lat0, lat1, lon0, lon1, stride):
    # chlor_a dims = [time][altitude][latitude][longitude]; lat axis is north->south.
    u = (f"https://coastwatch.noaa.gov/erddap/griddap/{ds}.csv?chlor_a"
         f"%5B(last)%5D%5B0%5D%5B({lat0}):{stride}:({lat1})%5D%5B({lon0}):{stride}:({lon1})%5D")
    raw = _urlopen(u, 42).read().decode()
    rows = list(csv.reader(io.StringIO(raw)))[2:]
    if not rows:
        raise ValueError("empty grid")
    import numpy as np
    lats = sorted(set(float(r[2]) for r in rows)); lons = sorted(set(float(r[3]) for r in rows))
    li = {v: i for i, v in enumerate(lats)}; lo = {v: i for i, v in enumerate(lons)}
    g = np.full((len(lats), len(lons)), np.nan)
    date = rows[0][0][:10]
    for r in rows:
        v = r[4]
        if v not in ("", "NaN"):
            g[li[float(r[2])], lo[float(r[3])]] = float(v)
    if not np.isfinite(g).any():
        raise ValueError("grid is all-NaN")
    return lats, lons, g, date


def fetch_chl(lat0, lat1, lon0, lon1, stride):
    """Try each DINEOF dataset in CHL_DATASETS order; return the first that answers.

    Returns (lats, lons, grid, date, source_label). Raises the last error only if every
    dataset fails, so a single retired dataset ID can no longer silently drop the map.
    """
    errs = []
    for ds, label in CHL_DATASETS:
        try:
            lats, lons, g, date = _fetch_chl_one(ds, lat0, lat1, lon0, lon1, stride)
            return lats, lons, g, date, label
        except Exception as e:
            errs.append(f"{ds}: {type(e).__name__} {e}")
    raise RuntimeError("all chlorophyll datasets failed — " + " | ".join(errs))

def draw_map(lats, lons, g, date, markers, title, path, vmin, vmax):
    import numpy as np, matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import patheffects as pe
    cmap = plt.get_cmap("turbo").copy(); cmap.set_bad("#e9edf2")
    fig, ax = plt.subplots(figsize=(8, 8.6), dpi=140); fig.patch.set_facecolor("white")
    ext = [lons[0], lons[-1], lats[0], lats[-1]]
    im = ax.imshow(g, origin="lower", extent=ext, cmap=cmap, vmin=vmin, vmax=vmax,
                   aspect=1/math.cos(math.radians(float(np.mean(lats)))), interpolation="bilinear")
    levels = np.arange(math.floor(np.nanmin(g)), math.ceil(np.nanmax(g)) + 1, 1)
    ax.contour(np.linspace(ext[0], ext[1], g.shape[1]), np.linspace(ext[2], ext[3], g.shape[0]),
               g, levels=levels, colors="k", linewidths=0.3, alpha=0.30)
    for name, la, lo2 in markers:
        ax.plot(lo2, la, "o", ms=5, mfc="white", mec="#11161d", mew=1.2, zorder=5)
        t = ax.text(lo2 + 0.06, la + 0.03, name, fontsize=8.5, color="white", fontweight="bold", zorder=6)
        t.set_path_effects([pe.withStroke(linewidth=2.4, foreground="#11161d")])
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
    ax.set_title(title, fontsize=13, color="#2B4C7E", fontweight="bold", pad=10)
    ax.tick_params(labelsize=7, colors="#5b6470")
    cb = fig.colorbar(im, ax=ax, fraction=0.038, pad=0.02)
    cb.set_label("Sea surface temp (°F)", fontsize=8, color="#2B4C7E"); cb.ax.tick_params(labelsize=7)
    ax.text(0.5, -0.07, f"NOAA MUR 1 km SST · {date} · contour lines every 1°F",
            transform=ax.transAxes, ha="center", fontsize=7.5, color="#5b6470")
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight", facecolor="white"); plt.close()

def draw_chl(lats, lons, g, date, markers, title, path, source):
    import numpy as np, matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import patheffects as pe
    from matplotlib.colors import LinearSegmentedColormap, LogNorm
    # blue (clean offshore) -> green/khaki (productive / green water). Distinct from SST turbo
    # and from brand teal; intuitive "blue water vs green water" read for anglers.
    wc = LinearSegmentedColormap.from_list("watercolor",
        ["#0b1d51", "#15439b", "#1f86d0", "#37b6c4", "#54c98a", "#a8d84f", "#e6c63a", "#9c6b22"])
    wc.set_bad("#e9edf2")
    fig, ax = plt.subplots(figsize=(8, 8.6), dpi=140); fig.patch.set_facecolor("white")
    ext = [lons[0], lons[-1], lats[0], lats[-1]]
    g = np.clip(g, 0.03, 3.0)
    im = ax.imshow(g, origin="lower", extent=ext, cmap=wc, norm=LogNorm(vmin=0.03, vmax=3.0),
                   aspect=1/math.cos(math.radians(float(np.mean(lats)))), interpolation="bilinear")
    for name, la, lo2 in markers:
        ax.plot(lo2, la, "o", ms=5, mfc="white", mec="#11161d", mew=1.2, zorder=5)
        t = ax.text(lo2 + 0.06, la + 0.03, name, fontsize=8.5, color="white", fontweight="bold", zorder=6)
        t.set_path_effects([pe.withStroke(linewidth=2.4, foreground="#11161d")])
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
    ax.set_title(title, fontsize=13, color="#2B4C7E", fontweight="bold", pad=10)
    ax.tick_params(labelsize=7, colors="#5b6470")
    cb = fig.colorbar(im, ax=ax, fraction=0.038, pad=0.02, ticks=[0.03, 0.1, 0.3, 1, 3])
    cb.ax.set_yticklabels(["0.03", "0.1", "0.3", "1", "3"], fontsize=7)
    cb.set_label("Chlorophyll-a (mg/m³)  ·  blue = clean  →  green = productive", fontsize=8, color="#2B4C7E")
    try:
        lag = (TODAY - datetime.date.fromisoformat(date)).days
        stamp = f"{date} ({lag}-day lag)"
    except Exception:
        stamp = date
    ax.text(0.5, -0.07, f"{source} · {stamp}",
            transform=ax.transAxes, ha="center", fontsize=7.5, color="#5b6470")
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight", facecolor="white"); plt.close()

_SOCAL_MARKERS = [("Catalina",33.38,-118.42),("San Clemente I.",32.90,-118.55),("Tanner Bk",32.73,-119.12),
                  ("Cortez Bk",32.42,-119.20),("San Diego",32.70,-117.20),("Pt Conception",34.45,-120.47)]
_BAJA_MARKERS = [("Ensenada",31.85,-116.62),("Guadalupe I.",29.03,-118.28),("Cedros I.",28.20,-115.22),
                 ("The Ridge",25.30,-114.60),("Alijos Rocks",24.95,-115.73),("Mag Bay",24.60,-112.10)]

def build_maps():
    stamp = TODAY.strftime("%Y%m%d")
    out = {}
    mac = lambda p: os.path.join(PROJECT_MAC, "conditions_maps", os.path.basename(p))
    # --- SST temperature-break maps (NOAA MUR) ---
    try:
        la, lo, g, d = fetch_mur(31.0, 34.6, -121.0, -116.6, 5)
        p = os.path.join(MAPS_DIR, f"socal_temp_break_{stamp}.png")
        draw_map(la, lo, g, d, _SOCAL_MARKERS, "Southern California — Temperature Breaks", p, 60, 72)
        out["socal_sst"] = (mac(p), d)
    except Exception as e:
        out["socal_sst"] = (None, str(e))
    try:
        la, lo, g, d = fetch_mur(23.5, 32.2, -119.6, -111.6, 9)
        p = os.path.join(MAPS_DIR, f"baja_temp_break_{stamp}.png")
        draw_map(la, lo, g, d, _BAJA_MARKERS, "Northern + Central Baja — Temperature Breaks", p, 60, 82)
        out["baja_sst"] = (mac(p), d)
    except Exception as e:
        out["baja_sst"] = (None, str(e))
    # --- Chlorophyll / water-color maps (DINEOF gap-filled; see CHL_DATASETS) ---
    # stride 1: the surviving DINEOF products are 9 km (0.0833°), so decimating further
    # would leave too few cells to read a colour edge off.
    try:
        la, lo, g, d, src = fetch_chl(34.6, 31.0, -121.0, -116.6, 1)
        p = os.path.join(MAPS_DIR, f"socal_water_color_{stamp}.png")
        draw_chl(la, lo, g, d, _SOCAL_MARKERS, "Southern California — Water Color (Chlorophyll)", p, src)
        out["socal_chl"] = (mac(p), d)
    except Exception as e:
        out["socal_chl"] = (None, str(e))
    try:
        la, lo, g, d, src = fetch_chl(32.2, 23.5, -119.6, -111.6, 1)
        p = os.path.join(MAPS_DIR, f"baja_water_color_{stamp}.png")
        draw_chl(la, lo, g, d, _BAJA_MARKERS, "Northern + Central Baja — Water Color (Chlorophyll)", p, src)
        out["baja_chl"] = (mac(p), d)
    except Exception as e:
        out["baja_chl"] = (None, str(e))
    return out


# ---------------- Storm Watch (NOAA National Hurricane Center) ----------------
# Named East Pacific tropical storms / hurricanes assessed against the report regions.
# Sources (public, no key):
#   CurrentStorms.json  -> every active storm with its advisory links
#   TCM forecast/advisory text -> 12-hourly track points to 120 h, max wind, 34/50/64-kt radii
#   TWO outlook text + 7-day graphic -> formation odds for disturbances that are not yet named
NHC_CURRENT   = "https://www.nhc.noaa.gov/CurrentStorms.json"
NHC_TWO_TEXT  = "https://www.nhc.noaa.gov/text/MIATWOEP.shtml"
NHC_TWO_7DAY  = "https://www.nhc.noaa.gov/xgtwo/two_pac_7d0.png"
NHC_TWO_PAGE  = "https://www.nhc.noaa.gov/gtwo.php?basin=epac&fdays=7"
NHC_EPAC_PAGE = "https://www.nhc.noaa.gov/?epac"
STORM_IMPACT_NM = 60     # 34-kt wind field reaches within this many nm of a region point -> IMPACT
STORM_WATCH_NM  = 300    # closest approach under this -> WATCH
STORM_FORMATION_MIN_PCT = 60   # print a formation-outlook line only at/above this 7-day chance
STORM_MAX_CONES = 5      # Day One attachments are capped at 10; 4 maps + outlook + up to 5 cones

def _nm(lat1, lon1, lat2, lon2):
    """Great-circle distance in nautical miles."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1; dl = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 3440.07 * math.asin(math.sqrt(h))

def _fetch_text(url):
    raw = _urlopen(url, 30).read().decode("utf-8", "replace")
    m = re.search(r"<pre[^>]*>(.*?)</pre>", raw, re.S)
    if m:
        import html as _html
        return _html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))
    return raw

def _storm_label(cls, kt):
    cls = (cls or "").upper()
    if cls == "HU":
        cat = 1 if kt < 83 else 2 if kt < 96 else 3 if kt < 113 else 4 if kt < 137 else 5
        return f"Hurricane (Cat {cat})", "Hurricane"
    return {"TS": ("Tropical Storm", "TS"), "TD": ("Tropical Depression", "TD"),
            "STS": ("Subtropical Storm", "STS"), "STD": ("Subtropical Depression", "STD"),
            "PTC": ("Potential Tropical Cyclone", "PTC")}.get(cls, (cls or "System", cls or ""))

def _parse_tcm(text):
    """Track points from a TCM product: [(label, lat, lon, max_kt, r34_nm)]. Positions are N/W only
    (East Pacific). r34 is the largest 34-kt quadrant radius, 0 when not given."""
    pts = []
    m = re.search(r"CENTER LOCATED NEAR\s+([\d.]+)N\s+([\d.]+)W AT (\d\d)/(\d\d)\d\dZ", text)
    if m:
        mw = re.search(r"MAX SUSTAINED WINDS\s+(\d+) KT", text)
        r = re.search(r"MAX SUSTAINED WINDS.*?\n(?:.*\n){0,4}?34 KT\.+\s*(\d+)NE\s+(\d+)SE\s+(\d+)SW\s+(\d+)NW", text)
        pts.append((f"{m.group(3)}/{m.group(4)}Z", float(m.group(1)), -float(m.group(2)),
                    int(mw.group(1)) if mw else 0, max(map(int, r.groups())) if r else 0))
    for blk in re.finditer(r"(?:FORECAST|OUTLOOK) VALID (\d\d)/(\d\d)\d\dZ\s+([\d.]+)N\s+([\d.]+)W\s*\n"
                           r"MAX WIND\s+(\d+) KT.*?\n((?:\s*\d+ KT\.+.*\n)*)", text):
        dd, hh, la, lo, mw, radii = blk.groups()
        r = re.search(r"34 KT\.+\s*(\d+)NE\s+(\d+)SE\s+(\d+)SW\s+(\d+)NW", radii)
        pts.append((f"{dd}/{hh}Z", float(la), -float(lo), int(mw), max(map(int, r.groups())) if r else 0))
    return pts

def _tcm_day_label(label):
    """'12/00Z' -> 'Sat Sep 12' using the current month (rolls to next month when the day is behind)."""
    try:
        dd = int(label.split("/")[0])
        d = TODAY.replace(day=dd)
        if dd < TODAY.day - 20:
            d = (TODAY.replace(day=28) + datetime.timedelta(days=4)).replace(day=dd)
        return d.strftime("%a %b %-d")
    except Exception:
        return label

def _assess(points):
    """Per-region closest approach -> [(tier, region, dist_nm, when, r34)], worst first.
    tier is IMPACT, WATCH, or None."""
    hits = []
    for name, lat, lon, tier_ in REGIONS:
        best = None
        for (label, la, lo, kt, r34) in points:
            d = _nm(lat, lon, la, lo)
            if best is None or d < best[0]:
                best = (d, label, r34)
        if best is None:
            continue
        d, label, r34 = best
        t = "IMPACT" if d - r34 <= STORM_IMPACT_NM else "WATCH" if d <= STORM_WATCH_NM else None
        hits.append((t, name, d, label, r34))
    rank = {"IMPACT": 2, "WATCH": 1, None: 0}
    hits.sort(key=lambda h: (-rank[h[0]], h[2]))
    return hits

def _download_png(url, path):
    data = _urlopen(url, 30).read()
    if not data.startswith(b"\x89PNG"):
        raise ValueError("not a PNG response")
    with open(path, "wb") as f:
        f.write(data)
    return path

def _formation_lines():
    """One line per TWO paragraph whose 7-day formation chance meets STORM_FORMATION_MIN_PCT."""
    out = []
    text = _fetch_text(NHC_TWO_TEXT)
    for para in re.split(r"\n\s*\n", text):
        m = re.search(r"Formation chance through 7 days\.+\s*(\w+)\.+\s*(\d+) percent", para, re.I)
        if not m:
            continue
        pct = int(m.group(2))
        if pct < STORM_FORMATION_MIN_PCT:
            continue
        head = para.strip().split("\n")[0].rstrip(":").strip()
        out.append(f"- **Formation outlook:** {pct}% chance through 7 days ({m.group(1)}) — {head}. "
                   f"Not yet named; see the 7-day outlook graphic below.")
    return out

def storm_watch():
    """Returns (markdown_lines, images, pdf_rows).
    images: [(key, local_png_path, caption)] in insert order -- the 7-day outlook first, then one
    forecast cone per named storm. pdf_rows: [(storm, position, assessment)] for the briefing."""
    stamp = TODAY.strftime("%Y%m%d")
    lines, images, pdf_rows = [], [], []
    try:
        data = _get(NHC_CURRENT)
    except Exception as e:
        return ([f"**⛈️ Storm Watch** — unavailable this run (NHC CurrentStorms feed: {e})"], [], [])
    storms = [s for s in data.get("activeStorms", []) if str(s.get("id", "")).lower().startswith("ep")]
    hdr_time = ""
    for s in storms:
        try:
            t = datetime.datetime.fromisoformat(str(s.get("lastUpdate", "")).replace("Z", "+00:00")).astimezone()
            hdr_time = f" · advisory {t.strftime('%a %b %-d %-I:%M %p %Z')}"
            break
        except Exception:
            pass
    lines.append(f"**⛈️ Storm Watch** _(NOAA National Hurricane Center · East Pacific"
                 f"{hdr_time}; checked {datetime.datetime.now().strftime('%a %b %-d %-I:%M %p')})_")
    named = []
    for s in storms:
        cls = str(s.get("classification", "")).upper()
        kt = int(float(s.get("intensity", 0) or 0))
        long_label, short = _storm_label(cls, kt)
        name = s.get("name", "?")
        pts = []
        try:
            adv_url = (s.get("forecastAdvisory") or {}).get("url")
            if adv_url:
                pts = _parse_tcm(_fetch_text(adv_url))
        except Exception:
            pts = []
        if not pts:
            pts = [("now", float(s.get("latitudeNumeric")), float(s.get("longitudeNumeric")), kt, 0)]
        hits = _assess(pts)
        top = hits[0] if hits else (None, "", 0, "", 0)
        tier = top[0]
        # Named storms always print. A depression prints only when it threatens a region.
        if cls not in ("TS", "HU", "STS") and tier is None:
            continue
        named.append(name)
        pos = f"{s.get('latitude')} {s.get('longitude')}"
        mv = f"moving {compass(float(s.get('movementDir', 0) or 0))} {int(float(s.get('movementSpeed', 0) or 0))} kt"
        when = "now" if top[3] == "now" or top[3] == pts[0][0] else _tcm_day_label(top[3])
        approach = f"closest approach {top[1]} ~{top[2]:,.0f} nm ({when})"
        if tier == "IMPACT":
            regs = ", ".join(h[1] for h in hits if h[0] == "IMPACT")
            verdict = f"🔴 **IMPACT** — 34-kt winds forecast within {STORM_IMPACT_NM} nm of: {regs}"
        elif tier == "WATCH":
            regs = ", ".join(h[1] for h in hits if h[0] == "WATCH")
            verdict = f"🟠 **WATCH** — passes within {STORM_WATCH_NM} nm of: {regs}"
        else:
            verdict = "🟢 MONITOR — no regional impact forecast"
        page = (s.get("forecastGraphics") or {}).get("url") or NHC_EPAC_PAGE
        lines.append(f"- **{long_label} {name}** ({kt} kt) — {pos}, {mv} · {approach} · {verdict} · "
                     f"[NHC page]({page})")
        pdf_rows.append((f"{short} {name} ({kt} kt)", f"{pos}, {mv}", f"{tier or 'MONITOR'} · {approach}"))
        if len(images) < STORM_MAX_CONES:
            try:
                sid = str(s.get("id")).upper()          # e.g. EP142026
                num = sid[2:4]                          # storm number -> storm_graphics/EP14/
                cone_url = f"https://www.nhc.noaa.gov/storm_graphics/EP{num}/{sid}_5day_cone.png"
                slug = re.sub(r"[^a-z0-9]+", "_", name.lower())
                p = _download_png(cone_url, os.path.join(MAPS_DIR, f"storm_{slug}_{stamp}.png"))
                images.append((f"storm_{slug}", p, f"{long_label} {name} — NHC 5-day forecast cone"))
            except Exception as e:
                lines.append(f"  _(forecast-cone image unavailable: {e})_")
    if not named:
        lines.append("- 🟢 No named tropical storms or hurricanes in the East Pacific this week.")
    try:
        lines.extend(_formation_lines())
    except Exception as e:
        lines.append(f"- _(formation outlook unavailable: {e})_")
    lines.append(f"- 7-day outlook: [NHC East Pacific graphical outlook]({NHC_TWO_PAGE})")
    # The 7-day graphic goes FIRST in the storm image set: it shows every disturbance, named or not.
    try:
        p = _download_png(NHC_TWO_7DAY, os.path.join(MAPS_DIR, f"storm_outlook_{stamp}.png"))
        images.insert(0, ("storm_outlook", p, "Tropical / Hurricane — NOAA NHC East Pacific 7-day outlook"))
    except Exception as e:
        lines.append(f"  _(7-day outlook image unavailable: {e})_")
    lines.append(f"_Tiers: IMPACT = 34-kt wind field forecast within {STORM_IMPACT_NM} nm of a report "
                 f"region in 5 days · WATCH = closest approach under {STORM_WATCH_NM} nm · MONITOR = "
                 "named storm, no regional threat. Distances are to each region's representative point; "
                 "NHC track error averages ~100 nm at day 4._")
    return lines, images, pdf_rows

def stage_inbox(paths):
    """Copy produced images into Day One's sandbox-readable inbox. Returns the inbox paths in order,
    or [] if the group container is not present on this Mac."""
    import shutil
    parent = os.path.dirname(DAYONE_INBOX)
    if not os.path.isdir(parent):
        return []
    os.makedirs(DAYONE_INBOX, exist_ok=True)
    out = []
    for p in paths:
        dst = os.path.join(DAYONE_INBOX, os.path.basename(p))
        shutil.copyfile(p, dst)
        out.append(dst)
    return out

def build_pdf(week_range, moon_plain, rows, maps, storm=None):
    """Render a single brand-styled Conditions briefing PDF (region tables + 4 maps).
    Returns (mac_path, None) on success or (None, reason) on failure."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.utils import ImageReader
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                        TableStyle, Image as RLImage, PageBreak)
        from PIL import Image as PILImage
    except Exception as e:
        return (None, f"reportlab/PIL unavailable: {e}")

    NAVY = colors.HexColor("#2B4C7E"); TEAL = colors.HexColor("#2C7A6B")
    GREY = colors.HexColor("#5b6470")
    stamp = TODAY.strftime("%Y%m%d")
    path = os.path.join(BRIEF_DIR, f"conditions_{stamp}.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, title="Conditions Briefing",
                            topMargin=0.6*inch, bottomMargin=0.5*inch,
                            leftMargin=0.7*inch, rightMargin=0.7*inch)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=NAVY, fontSize=21, alignment=0, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=ss["Normal"], textColor=GREY, fontSize=10, spaceAfter=12)
    moon = ParagraphStyle("moon", parent=ss["Normal"], fontSize=11, textColor=colors.HexColor("#27424a"),
                          backColor=colors.HexColor("#eef3f1"), borderPadding=9, leading=15, spaceAfter=14)
    hsec = ParagraphStyle("hsec", parent=ss["Heading2"], textColor=TEAL, fontSize=11, spaceBefore=8, spaceAfter=6)
    cap = ParagraphStyle("cap", parent=ss["Normal"], fontSize=8, textColor=GREY, alignment=1, spaceAfter=2)
    foot = ParagraphStyle("foot", parent=ss["Normal"], fontSize=7.5, textColor=GREY, spaceBefore=10)

    story = [Paragraph("Conditions Briefing", h1),
             Paragraph(f"Week of {week_range} &nbsp;&middot;&nbsp; SoCal &amp; Baja", sub),
             Paragraph(moon_plain, moon)]

    def region_table(tier, title):
        body = [["Region", "Wind", "Swell", "SST"]]
        for (name, t, wind, swell, sst) in rows:
            if t == tier:
                body.append([name, wind, swell, sst])
        if len(body) == 1:
            return
        story.append(Paragraph(title, hsec))
        tbl = Table(body, colWidths=[1.55*inch, 1.6*inch, 2.05*inch, 0.95*inch], hAlign="LEFT")
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#dde3ea")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(tbl)

    region_table("core", "CORE REGIONS")
    region_table("bank", "OFFSHORE BANKS (modeled)")

    # Maps — open the local PNG, flatten to RGB, write a temp JPEG (reportlab Image needs a path).
    import tempfile
    tmpdir = tempfile.mkdtemp()
    def flow(local, w=3.35*inch):
        im = PILImage.open(local).convert("RGB")
        jp = os.path.join(tmpdir, os.path.basename(local).replace(".png", ".jpg"))
        im.save(jp, "JPEG", quality=88)
        return RLImage(jp, width=w, height=w * im.height / im.width)

    order = [("socal_sst", "SoCal — Temperature Breaks"), ("baja_sst", "Baja — Temperature Breaks"),
             ("socal_chl", "SoCal — Water Color"), ("baja_chl", "Baja — Water Color")]
    avail = []
    for key, label in order:
        v = maps.get(key)
        if v and v[0]:
            avail.append((label, os.path.join(MAPS_DIR, os.path.basename(v[0]))))
    if avail:
        story.append(PageBreak())
        story.append(Paragraph("Temperature-Break &amp; Water-Color Maps", hsec))
        for i in range(0, len(avail), 2):
            pair = avail[i:i+2]
            imgs = [flow(p) for _, p in pair]
            caps = [Paragraph(lbl, cap) for lbl, _ in pair]
            while len(imgs) < 2:
                imgs.append(""); caps.append("")
            t = Table([imgs, caps], colWidths=[3.6*inch, 3.6*inch], hAlign="CENTER")
            t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                   ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
                                   ("BOTTOMPADDING", (0, 1), (-1, 1), 10)]))
            story.append(t)
    # Storm Watch page: text rows + the 7-day outlook + forecast cones.
    if storm:
        s_lines, s_images, s_rows = storm
        story.append(PageBreak())
        story.append(Paragraph("Storm Watch — NOAA National Hurricane Center (East Pacific)", hsec))
        body = [["Storm", "Position / motion", "Assessment"]]
        for r in s_rows:
            body.append(list(r))
        if len(body) == 1:
            body.append(["No named storms", "", "East Pacific clear this week"])
        tbl = Table(body, colWidths=[1.7*inch, 2.1*inch, 3.3*inch], hAlign="LEFT")
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7.8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#dde3ea")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 6)]))
        story.append(tbl)
        for ln in s_lines[1:]:
            if ln.startswith("- ") or ln.startswith("_"):
                txt = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", ln)   # drop markdown links
                story.append(Paragraph(_plain(txt).replace("&", "&amp;"), cap))
        for key, local, caption in s_images:
            try:
                im = PILImage.open(local)
                w = 6.6*inch
                story.append(Spacer(1, 8))
                story.append(RLImage(local, width=w, height=w * im.height / im.width))
                story.append(Paragraph(caption, cap))
            except Exception:
                pass
    story.append(Paragraph("Numbers: Open-Meteo (wind/swell/SST). Temp-break maps: NOAA MUR 1&nbsp;km SST. "
                           "Water-color maps: DINEOF gap-filled chlorophyll (dataset and lag printed "
                           "under each map). Storm Watch: NOAA NHC. Moon: ephem. Baja offshore values are modeled.", foot))
    try:
        doc.build(story)
    except Exception as e:
        return (None, f"PDF build failed: {e}")
    return (os.path.join(PROJECT_MAC, "conditions_briefings", os.path.basename(path)), None)


def main():
    rng = f"{TODAY.strftime('%b %-d')} – {WEEK_END.strftime('%b %-d, %Y')}"
    data = {}
    for name, lat, lon, tier in REGIONS:
        try:
            data[name] = fetch_region(lat, lon)
        except Exception as e:
            data[name] = {"wind": f"(unavailable: {e})", "swell": "", "sst": ""}
    rows = [(name, tier, data[name]["wind"], data[name]["swell"], data[name]["sst"])
            for (name, lat, lon, tier) in REGIONS]
    maps = build_maps()
    try:
        storm = storm_watch()
    except Exception as e:
        storm = ([f"**⛈️ Storm Watch** — unavailable this run ({e})"], [], [])
    moon_md = moon_line()
    pdf = build_pdf(rng, _plain(moon_md), rows, maps, storm)
    prune_old()

    # ---- image set, in entry order: the 4 Conditions maps, then the storm images ----
    map_order = [("socal_sst", "SoCal — temperature breaks (NOAA MUR SST)"),
                 ("socal_chl", "SoCal — water color (chlorophyll)"),
                 ("baja_sst",  "Baja — temperature breaks (NOAA MUR SST)"),
                 ("baja_chl",  "Baja — water color (chlorophyll)")]
    cond_images = []
    for key, caption in map_order:
        v = maps.get(key)
        if v and v[0]:
            cond_images.append((key, os.path.join(MAPS_DIR, os.path.basename(v[0])), caption))
    storm_lines, storm_images, _ = storm
    all_images = cond_images + storm_images
    inbox = stage_inbox([p for _, p, _ in all_images])
    placeholders = bool(inbox)
    stamp = TODAY.strftime("%Y%m%d")
    with open(os.path.join(MAPS_DIR, f"attachments_{stamp}.txt"), "w") as f:
        f.write("\n".join(inbox) + ("\n" if inbox else ""))

    out = []
    out.append(f"## \U0001F30A Conditions — Week of {rng}\n")
    out.append(moon_md + "\n")
    out.append("**Core regions**\n")
    for name, lat, lon, tier in REGIONS:
        if tier != "core": continue
        d = data[name]
        out.append(f"- **{name}** — Wind {d['wind']} · Swell {d['swell']} · SST {d['sst']}")
    out.append("\n**Offshore banks** _(modeled — include a line below ONLY if this week's "
               "YouTube/long-range reports mention that area; otherwise omit it)_\n")
    for name, lat, lon, tier in REGIONS:
        if tier != "bank": continue
        d = data[name]
        out.append(f"- **{name}** — Wind {d['wind']} · Swell {d['swell']} · SST {d['sst']}")
    out.append("")
    n_maps = len(cond_images)
    if pdf[0]:
        out.append(f"📄 **Visual briefing:** {n_maps} temp-break + water-color maps below; the full "
                   "briefing (maps + Storm Watch) is also saved as a PDF in the project folder:")
        out.append(f"`{pdf[0]}`")
    else:
        out.append(f"_Visual briefing PDF unavailable this run ({pdf[1]})._")
    if placeholders:
        for key, p, caption in cond_images:
            out.append(f"\n_{caption}_")
            out.append("[{attachment}]")
    elif cond_images:
        out.append("_(Day One inbox not present on this Mac — maps are in the PDF only.)_")
    out.append("")
    out.extend(storm_lines)
    if placeholders:
        for key, p, caption in storm_images:
            out.append(f"\n_{caption}_")
            out.append("[{attachment}]")
    out.append("")

    print("\n".join(out))
    # Machine-readable footers: the briefing PDF path, and the ordered attachment list the run
    # must pass VERBATIM as `attachments=` to create_journal_entry (one [{attachment}] above per line).
    print("\n<!-- BRIEFING")
    if pdf[0]:
        print(pdf[0])
    print("-->")
    print("<!-- ATTACHMENTS")
    for p in inbox:
        print(p)
    print("-->")

if __name__ == "__main__":
    main()
