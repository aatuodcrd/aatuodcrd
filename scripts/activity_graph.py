#!/usr/bin/env python3
"""Render a 1-year contribution area graph as SVG (dark + light)."""
import json, os, urllib.request
from datetime import date

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

W, H, PAD_L, PAD_B, PAD_T = 820, 220, 34, 26, 18

def svg(days, line, area, text, grid):
    n = len(days)
    counts = [d["contributionCount"] for d in days]
    top = max(max(counts), 1)
    x = lambda i: PAD_L + i * (W - PAD_L - 10) / (n - 1)
    y = lambda c: PAD_T + (1 - c / top) * (H - PAD_T - PAD_B)
    pts = " ".join(f"{x(i):.1f},{y(c):.1f}" for i, c in enumerate(counts))
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">']
    # horizontal grid + y labels
    for f in (0, 0.5, 1):
        c = top * f
        out.append(f'<line x1="{PAD_L}" x2="{W-10}" y1="{y(c):.1f}" y2="{y(c):.1f}" stroke="{grid}" stroke-width="1"/>')
        out.append(f'<text x="{PAD_L-6}" y="{y(c)+4:.1f}" fill="{text}" font-size="10" text-anchor="end">{round(c)}</text>')
    out.append(f'<polygon fill="{area}" fill-opacity="0.45" points="{x(0):.1f},{H-PAD_B:.1f} {pts} {x(n-1):.1f},{H-PAD_B:.1f}"/>')
    out.append(f'<polyline fill="none" stroke="{line}" stroke-width="2" stroke-linejoin="round" points="{pts}"/>')
    # month ticks on the 1st of each month
    for i, d in enumerate(days):
        dt = date.fromisoformat(d["date"])
        if dt.day == 1:
            out.append(f'<text x="{x(i):.1f}" y="{H-8}" fill="{text}" font-size="10" text-anchor="middle">{dt.strftime("%b")}</text>')
    out.append("</svg>")
    return "\n".join(out)

if __name__ == "__main__":
    days = fetch()
    assert len(days) > 300, len(days)
    for name, colors in {
        "assets/activity-dark.svg": ("#5fb3b3", "#0b486b", "#8b949e", "#21262d"),
        "assets/activity-light.svg": ("#0b486b", "#a5d8d8", "#57606a", "#e6e8eb"),
    }.items():
        os.makedirs("assets", exist_ok=True)
        open(name, "w").write(svg(days, *colors))
        print("wrote", name)
