"""Builds two SVGs from the GitHub contribution API: a calendar heatmap and an activity overview radar."""
import json, os, sys, math, datetime, urllib.request

USER = os.environ.get("GH_USER", "Anasabubakar")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist"
MOCK = os.environ.get("MOCK_JSON")

QUERY = """query($login:String!){user(login:$login){contributionsCollection{
totalCommitContributions totalIssueContributions totalPullRequestContributions
totalPullRequestReviewContributions restrictedContributionsCount
contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""

def fetch():
    if MOCK:
        return json.load(open(MOCK))
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    if "errors" in d:
        raise SystemExit(d["errors"])
    return d["data"]["user"]["contributionsCollection"]

BG, FG, MUTED, LINE = "#0d1117", "#e6edf3", "#7d8590", "#30363d"
LEVELS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

def calendar(c):
    cal = c["contributionCalendar"]
    days = [d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]]
    top = max(days) if days else 1
    def lvl(n):
        if n == 0: return 0
        q = n / top
        return 1 if q <= .25 else 2 if q <= .5 else 3 if q <= .75 else 4
    cell, gap, x0, y0 = 11, 3, 40, 46
    w = x0 + len(cal["weeks"]) * (cell + gap) + 20
    h = y0 + 7 * (cell + gap) + 40
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="Segoe UI,Arial,sans-serif">',
         f'<rect width="100%" height="100%" rx="6" fill="{BG}" stroke="{LINE}"/>',
         f'<text x="16" y="22" fill="{FG}" font-size="13" font-weight="600">{cal["totalContributions"]:,} contributions in the last year</text>']
    last_m = None
    for i, wk in enumerate(cal["weeks"]):
        for j, d in enumerate(wk["contributionDays"]):
            dt = datetime.date.fromisoformat(d["date"])
            if j == 0 and dt.month != last_m and dt.day <= 14:
                s.append(f'<text x="{x0+i*(cell+gap)}" y="{y0-6}" fill="{MUTED}" font-size="10">{dt.strftime("%b")}</text>')
                last_m = dt.month
            s.append(f'<rect x="{x0+i*(cell+gap)}" y="{y0+j*(cell+gap)}" width="{cell}" height="{cell}" rx="2" fill="{LEVELS[lvl(d["contributionCount"])]}"><title>{d["date"]}: {d["contributionCount"]}</title></rect>')
    for j, n in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        s.append(f'<text x="8" y="{y0+j*(cell+gap)+9}" fill="{MUTED}" font-size="10">{n}</text>')
    ly = y0 + 7 * (cell + gap) + 12
    lx = w - 20 - 5 * (cell + gap) - 70
    s.append(f'<text x="{lx}" y="{ly+9}" fill="{MUTED}" font-size="10">Less</text>')
    for k, col in enumerate(LEVELS):
        s.append(f'<rect x="{lx+30+k*(cell+gap)}" y="{ly}" width="{cell}" height="{cell}" rx="2" fill="{col}"/>')
    s.append(f'<text x="{lx+34+5*(cell+gap)}" y="{ly+9}" fill="{MUTED}" font-size="10">More</text></svg>')
    return "\n".join(s)

def radar(c):
    vals = {"Commits": c["totalCommitContributions"], "Issues": c["totalIssueContributions"],
            "Pull requests": c["totalPullRequestContributions"], "Code review": c["totalPullRequestReviewContributions"]}
    tot = sum(vals.values()) or 1
    pct = {k: v / tot for k, v in vals.items()}
    W, H, cx, cy, R = 420, 230, 210, 115, 78
    axes = {"Commits": (-1, 0), "Issues": (1, 0), "Pull requests": (0, 1), "Code review": (0, -1)}
    m = max(pct.values()) or 1
    pts = [(cx + axes[k][0] * R * pct[k] / m, cy + axes[k][1] * R * pct[k] / m) for k in axes]
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI,Arial,sans-serif">',
         f'<rect width="100%" height="100%" rx="6" fill="{BG}" stroke="{LINE}"/>',
         f'<text x="16" y="26" fill="{FG}" font-size="13" font-weight="600">Activity overview</text>',
         f'<line x1="{cx-R}" y1="{cy}" x2="{cx+R}" y2="{cy}" stroke="#238636" stroke-width="1.5"/>',
         f'<line x1="{cx}" y1="{cy-R}" x2="{cx}" y2="{cy+R}" stroke="#238636" stroke-width="1.5"/>',
         f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)}" fill="#26a641" fill-opacity="0.35" stroke="#39d353" stroke-width="1.5"/>']
    for x, y in pts:
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{BG}" stroke="#39d353" stroke-width="2"/>')
    lab = {"Code review": (cx, cy-R-18, "middle"), "Pull requests": (cx, cy+R+14, "middle"),
           "Commits": (cx-R-12, cy+4, "end"), "Issues": (cx+R+12, cy+4, "start")}
    for k, (x, y, a) in lab.items():
        dy = -2 if k == "Code review" else 12 if k == "Pull requests" else 0
        s.append(f'<text x="{x}" y="{y}" text-anchor="{a}" fill="{FG}" font-size="11">{round(pct[k]*100)}%</text>')
        s.append(f'<text x="{x}" y="{y+13}" text-anchor="{a}" fill="{MUTED}" font-size="11">{k}</text>')
    s.append("</svg>")
    return "\n".join(s)

c = fetch()
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "contribution-graph.svg"), "w").write(calendar(c))
open(os.path.join(OUT, "activity-overview.svg"), "w").write(radar(c))
print("ok", c["contributionCalendar"]["totalContributions"])
