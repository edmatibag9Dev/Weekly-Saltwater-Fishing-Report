#!/usr/bin/env python3
"""
Weekly Conditions generator for the Saltwater Fishing Report.

Produces:
  1. A Markdown "Conditions" section printed to stdout (capture this into the report).
  2. Two temperature-break PNG maps written to ./conditions_maps/ .

Data sources (no Chrome, no login required):
  - Wind / swell / SST numbers ....... Open-Meteo Marine + Weather APIs
  - Temperature-break maps ........... NOAA MUR 1 km SST via NOAA CoastWatch ERDDAP
  - Moon phase ....................... ephem (falls back to an approximation)

Safe to re-run. Degrades gracefully: if the map server is unavailable the text
still prints and the maps are reported as unavailable.

Run deps once per environment:
  pip install matplotlib numpy ephem --break-system-packages -q
"""
import os, sys, math, csv, io, json, re, glob, datetime, urllib.request

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

def _plain(s):
    """Strip markdown bold/italic and emoji for PDF text (reportlab core fonts lack emoji glyphs)."""
    s = s.replace("**", "").replace("_", "")
    return "".join(c for c in s if ord(c) < 0x2600).strip()

def prune_old(days=56):
    """Delete map/briefing files older than ~8 weeks so the folders don't grow forever."""
    cutoff = datetime.datetime.now().timestamp() - days * 86400
    for d in (MAPS_DIR, BRIEF_DIR):
        for f in glob.glob(os.path.join(d, "*")):
            try:
                if os.path.isfile(f) and os.path.getmtime(f) < cutoff:
                    os.remove(f)
            except OSError:
                pass

# VIIRS SNPP + NOAA-20 + Sentinel-3A OLCI, DINEOF gap-filled chlorophyll (daily, 2 km).
# Gap-filled = clean single-frame coverage (clouds interpolated). ~10-day science lag.
CHL_DS = "noaacwNPPN20S3ASCIDINEOF2kmDaily"
_UA = {"User-Agent": "Mozilla/5.0 (conditions.py fishing-report)"}
def _urlopen(url, timeout=30):
    return urllib.request.urlopen(urllib.request.Request(url, headers=_UA), timeout=timeout)

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

def fetch_chl(lat0, lat1, lon0, lon1, stride):
    # chlor_a dims = [time][altitude][latitude][longitude]; lat axis is north->south.
    u = (f"https://coastwatch.noaa.gov/erddap/griddap/{CHL_DS}.csv?chlor_a"
         f"%5B(last)%5D%5B0%5D%5B({lat0}):{stride}:({lat1})%5D%5B({lon0}):{stride}:({lon1})%5D")
    raw = _urlopen(u, 42).read().decode()
    rows = list(csv.reader(io.StringIO(raw)))[2:]
    import numpy as np
    lats = sorted(set(float(r[2]) for r in rows)); lons = sorted(set(float(r[3]) for r in rows))
    li = {v: i for i, v in enumerate(lats)}; lo = {v: i for i, v in enumerate(lons)}
    g = np.full((len(lats), len(lons)), np.nan)
    date = rows[0][0][:10]
    for r in rows:
        v = r[4]
        if v not in ("", "NaN"):
            g[li[float(r[2])], lo[float(r[3])]] = float(v)
    return lats, lons, g, date

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

def draw_chl(lats, lons, g, date, markers, title, path):
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
    ax.text(0.5, -0.07, f"VIIRS SNPP+NOAA-20 + Sentinel-3A OLCI · DINEOF gap-filled · {date}",
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
    # --- Chlorophyll / water-color maps (VIIRS+OLCI DINEOF, gap-filled) ---
    try:
        la, lo, g, d = fetch_chl(34.6, 31.0, -121.0, -116.6, 2)
        p = os.path.join(MAPS_DIR, f"socal_water_color_{stamp}.png")
        draw_chl(la, lo, g, d, _SOCAL_MARKERS, "Southern California — Water Color (Chlorophyll)", p)
        out["socal_chl"] = (mac(p), d)
    except Exception as e:
        out["socal_chl"] = (None, str(e))
    try:
        la, lo, g, d = fetch_chl(32.2, 23.5, -119.6, -111.6, 4)
        p = os.path.join(MAPS_DIR, f"baja_water_color_{stamp}.png")
        draw_chl(la, lo, g, d, _BAJA_MARKERS, "Northern + Central Baja — Water Color (Chlorophyll)", p)
        out["baja_chl"] = (mac(p), d)
    except Exception as e:
        out["baja_chl"] = (None, str(e))
    return out

def build_pdf(week_range, moon_plain, rows, maps):
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
    story.append(Paragraph("Numbers: Open-Meteo (wind/swell/SST). Temp-break maps: NOAA MUR 1&nbsp;km SST. "
                           "Water-color maps: VIIRS+OLCI DINEOF gap-filled chlorophyll. Moon: ephem. "
                           "Baja offshore values are modeled.", foot))
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
    moon_md = moon_line()
    pdf = build_pdf(rng, _plain(moon_md), rows, maps)
    prune_old()

    out = []
    out.append(f"## \U0001F30A Conditions — Week of {rng}\n")
    out.append(moon_line() + "\n")
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
    n_maps = sum(1 for k in ("socal_sst", "baja_sst", "socal_chl", "baja_chl") if maps.get(k) and maps[k][0])
    if pdf[0]:
        out.append(f"📄 **Visual briefing:** the {n_maps} temp-break + water-color maps are in a one-page "
                   "PDF saved to the project folder:")
        out.append(f"`{pdf[0]}`")
        out.append("_Open it from the folder, or drag the PDF into this Day One entry to embed it "
                   "(Day One renders manually-attached files)._")
    else:
        out.append(f"_Visual briefing PDF unavailable this run ({pdf[1]})._")

    print("\n".join(out))
    # Machine-readable footer: the briefing PDF path for the run to reference.
    print("\n<!-- BRIEFING")
    if pdf[0]:
        print(pdf[0])
    print("-->")

if __name__ == "__main__":
    main()
