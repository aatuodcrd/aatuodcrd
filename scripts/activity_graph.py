#!/usr/bin/env python3
"""Render a 1-year contribution card as SVG (dark + light): stats header + weekly area chart."""
import json, os, sys, urllib.request
from datetime import date, timedelta

USER = os.environ.get("GH_USER", "aatuodcrd")
Q = """query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{
weeks{contributionDays{date contributionCount}}}}}}"""

def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        json.dumps({"query": Q, "variables": {"u": USER}}).encode(),
        {"Authorization": "bearer " + os.environ["GH_TOKEN"], "Content-Type": "application/json"},
    )
    cal = json.load(urllib.request.urlopen(req))["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return [d for w in cal["weeks"] for d in w["contributionDays"]]

def stats(days):
    c = [d["contributionCount"] for d in days]
    longest = run = 0
    for n in c:
        run = run + 1 if n else 0
        longest = max(longest, run)
    # today still in progress: a 0 today doesn't break the streak yet
    tail = c[:-1] if c and c[-1] == 0 else c
    current = 0
    for n in reversed(tail):
        if not n:
            break
        current += 1
    best = max(days, key=lambda d: d["contributionCount"])
    return sum(c), current, longest, best

def weekly(days):
    start = date.fromisoformat(days[0]["date"])
    start -= timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday, like GitHub's calendar
    weeks = {}
    for d in days:
        dt = date.fromisoformat(d["date"])
        weeks.setdefault((dt - start).days // 7, [dt, 0])[1] += d["contributionCount"]
    return [weeks[k] for k in sorted(weeks)]

W, H = 880, 300
CX0, CX1, CY0, CY1 = 48, W - 28, 118, H - 40  # chart box

def svg(days, p):
    total, current, longest, best = stats(days)
    wk = weekly(days)
    top = max(max(v for _, v in wk), 1)
    n = len(wk)
    x = lambda i: CX0 + i * (CX1 - CX0) / (n - 1)
    y = lambda v: CY1 - v / top * (CY1 - CY0)
    pts = [(x(i), y(v)) for i, (_, v) in enumerate(wk)]
    # horizontal-midpoint beziers: smooth, never overshoots below 0 or above the peak
    path = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}" + "".join(
        f" C{(x0 + x1) / 2:.1f},{y0:.1f} {(x0 + x1) / 2:.1f},{y1:.1f} {x1:.1f},{y1:.1f}"
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]))
    area = f"{path} L{CX1:.1f},{CY1} L{CX0:.1f},{CY1} Z"
    bd = date.fromisoformat(best["date"])
    tiles = [
        (f"{total:,}", "contributions · past year"),
        (f"{current} d", "current streak"),
        (f"{longest} d", "longest streak"),
        (f"{best['contributionCount']}", f"busiest day · {bd.strftime('%b')} {bd.day}"),
    ]
    o = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{total} contributions in the last year; current streak {current} days; longest streak {longest} days">
<style>
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:{p["muted"]}}}
.v{{font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;font-weight:700;font-size:26px;fill:{p["text"]}}}
.l{{font-size:11px}} .t{{font-size:10px}}
.line{{stroke-dasharray:4000;stroke-dashoffset:4000;animation:draw 2.2s ease-out forwards}}
.fade{{opacity:0;animation:fade .8s 1.4s ease-out forwards}}
@keyframes draw{{to{{stroke-dashoffset:0}}}} @keyframes fade{{to{{opacity:1}}}}
@media (prefers-reduced-motion:reduce){{.line{{animation:none;stroke-dashoffset:0}}.fade{{animation:none;opacity:1}}}}
</style>
<defs>
<linearGradient id="stroke" x1="0" x2="1"><stop offset="0" stop-color="{p["a1"]}"/><stop offset="1" stop-color="{p["a2"]}"/></linearGradient>
<linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{p["a1"]}" stop-opacity=".35"/><stop offset="1" stop-color="{p["a1"]}" stop-opacity="0"/></linearGradient>
</defs>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12" fill="{p["bg"]}" stroke="{p["line"]}"/>''']
    for i, (v, l) in enumerate(tiles):
        tx = 28 + i * (W - 56) / 4
        if i:
            o.append(f'<line x1="{tx - 14:.1f}" x2="{tx - 14:.1f}" y1="28" y2="78" stroke="{p["line"]}"/>')
        o.append(f'<text class="v" x="{tx:.1f}" y="58">{v}</text><text class="l" x="{tx:.1f}" y="78">{l}</text>')
    for f in (0, 0.5, 1):
        o.append(f'<line x1="{CX0}" x2="{CX1}" y1="{y(top * f):.1f}" y2="{y(top * f):.1f}" stroke="{p["line"]}" stroke-dasharray="{"" if f == 0 else "2 4"}"/>')
        o.append(f'<text class="t" x="{CX0 - 8}" y="{y(top * f) + 3:.1f}" text-anchor="end">{round(top * f)}</text>')
    seen = set()
    for i, (dt, _) in enumerate(wk):
        if i and (dt.year, dt.month) not in seen:  # first week that starts in a new month
            o.append(f'<text class="t" x="{x(i):.1f}" y="{H - 18}" text-anchor="middle">{dt.strftime("%b")}</text>')
        seen.add((dt.year, dt.month))
    o.append(f'<path class="fade" d="{area}" fill="url(#fill)"/>')
    o.append(f'<path class="line" d="{path}" fill="none" stroke="url(#stroke)" stroke-width="2.5" stroke-linecap="round"/>')
    pi = max(range(n), key=lambda i: wk[i][1])
    px, py = pts[pi]
    anchor = "end" if px > W - 140 else "start"
    o.append(f'<g class="fade"><circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{p["bg"]}" stroke="{p["a2"]}" stroke-width="2"/>'
             f'<text class="t" x="{px + (-10 if anchor == "end" else 10):.1f}" y="{py + 4:.1f}" text-anchor="{anchor}">peak week · {wk[pi][1]}</text></g>')
    o.append(f'<text class="t" x="{CX0}" y="{CY0 - 14}">contributions / week</text>')
    o.append("</svg>")
    return "\n".join(o)

PALETTES = {  # matches aatuodcrd.github.io tokens
    "assets/activity-card-dark.svg": dict(bg="#0d1117", line="#262c33", text="#e7ecef", muted="#8a939c", a1="#4fd1c5", a2="#8b8bf5"),
    "assets/activity-card-light.svg": dict(bg="#ffffff", line="#e3e6e8", text="#0b0d10", muted="#565f68", a1="#0d7d8c", a2="#5757d6"),
}

if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        d = lambda s, n: {"date": s, "contributionCount": n}
        t, cur, lon, best = stats([d("2026-01-01", 1), d("2026-01-02", 0), d("2026-01-03", 2), d("2026-01-04", 3), d("2026-01-05", 0)])
        assert (t, cur, lon, best["contributionCount"]) == (6, 2, 2, 3), (t, cur, lon)
        assert stats([d("2026-01-01", 1), d("2026-01-02", 0), d("2026-01-03", 5)])[1] == 1
        print("ok"); sys.exit()
    days = json.load(open(sys.argv[1])) if sys.argv[1:] else fetch()
    assert len(days) > 300, len(days)
    os.makedirs("assets", exist_ok=True)
    for name, p in PALETTES.items():
        open(name, "w").write(svg(days, p))
        print("wrote", name)
