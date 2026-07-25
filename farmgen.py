import os, re
LOGDIR = r"C:/Users/Public/Daybreak Game Company/Installed Games/EverQuest/Logs"
OUT = r"C:/Users/Dercius/Desktop/EQFarmLog/farm_log.html"
DAYS = [("22", "Jul 22"), ("23", "Jul 23"), ("24", "Jul 24")]
TOONS = ["Zedus", "Dercius", "Emia", "Hoggly"]
GROUP = set(["Zedus", "Dercius", "Emia", "Hoggly", "Thrice", "Loriex", "Hogga", "Discover", "Froggy"])


def readlines(name):
    p = os.path.join(LOGDIR, "eqlog_%s_frostreaver.txt" % name)
    if not os.path.exists(p):
        return []
    with open(p, "rb") as f:
        raw = f.read()
    return raw.decode("latin-1").split("\n")


def day_ok(line, dd):
    return len(line) > 25 and line[5:8] == "Jul" and line[9:11] == dd and line[21:25] == "2026"


def secs(line):
    try:
        return int(line[12:14]) * 3600 + int(line[15:17]) * 60 + int(line[18:20])
    except Exception:
        return -1


re_melee = re.compile(r"\] You ([a-z]+) .* for (\d+) points of damage")
re_spec = re.compile(r"\] You (?:flying kick|round kick|tiger claw|eagle strike|dragon punch) .* for (\d+) point")
re_dot = re.compile(r" has taken (\d+) damage from your ")
re_proc = re.compile(r"\] You hit .* for (\d+) points of (?:magic|fire|cold|poison|disease|chromatic) damage by (.+?)\.")
re_coin = re.compile(r"as your split")
re_plat = re.compile(r"(\d+) platinum")
re_gold = re.compile(r"(\d+) gold")
re_sil = re.compile(r"(\d+) silver")
re_cop = re.compile(r"(\d+) copper")


def coinval(line):
    def g(r):
        m = r.search(line)
        return int(m.group(1)) if m else 0
    return (g(re_plat) * 1000 + g(re_gold) * 100 + g(re_sil) * 10 + g(re_cop)) / 1000.0


def detect_pet(dd):
    cnt = {}
    hitre = re.compile(r"\] ([A-Z][a-z]+) (?:hits|slashes|bites|claws|mauls|crushes|pierces) a ")
    for l in readlines("Hoggly"):
        if not day_ok(l, dd):
            continue
        m = hitre.search(l)
        if m and m.group(1) not in GROUP:
            cnt[m.group(1)] = cnt.get(m.group(1), 0) + 1
    return [n for n, c in cnt.items() if c > 20]


def parse_day(dd):
    d = {"toons": {}}
    pets = detect_pet(dd)
    for t in ["Zedus", "Dercius", "Emia"]:
        td = {"melee": 0, "backstab": 0, "kick": 0, "spec": 0, "dot": 0, "proc": {}, "total": 0}
        for l in readlines(t):
            if not day_ok(l, dd):
                continue
            m = re_melee.search(l)
            if m:
                n = int(m.group(2)); v = m.group(1)
                if v == "backstab":
                    td["backstab"] += n
                elif v == "kick":
                    td["kick"] += n
                else:
                    td["melee"] += n
                td["total"] += n; continue
            m = re_spec.search(l)
            if m:
                n = int(m.group(1)); td["spec"] += n; td["total"] += n; continue
            m = re_dot.search(l)
            if m:
                n = int(m.group(1)); td["dot"] += n; td["total"] += n; continue
            m = re_proc.search(l)
            if m:
                n = int(m.group(1)); pr = m.group(2)
                td["proc"][pr] = td["proc"].get(pr, 0) + n; td["total"] += n; continue
        d["toons"][t] = td
    petdmg = 0
    if pets:
        petre = re.compile(r"\] (?:%s) .* for (\d+) point" % ("|".join(pets)))
        for l in readlines("Hoggly"):
            if not day_ok(l, dd):
                continue
            m = petre.search(l)
            if m:
                petdmg += int(m.group(1))
    d["pet"] = petdmg
    d["petname"] = ", ".join(pets) if pets else "-"
    coin = 0.0
    for t in TOONS:
        for l in readlines(t):
            if day_ok(l, dd) and re_coin.search(l):
                coin += coinval(l)
    d["coin"] = coin
    vend = 0.0
    for l in readlines("Hogga"):
        if day_ok(l, dd) and " for the " in l and "You receive" in l:
            vend += coinval(l)
    d["vendor"] = vend
    pend = {}; pc = 0.0; pcn = 0
    off = re.compile(r"([A-Za-z]+) has offered you ([0-9,]+) platinum")
    comp = re.compile(r"You complete the trade with ([A-Za-z]+)")
    canc = re.compile(r"([A-Za-z]+) has cancelled the trade")
    for l in readlines("Discover"):
        if not day_ok(l, dd):
            continue
        m = off.search(l)
        if m:
            pend[m.group(1)] = float(m.group(2).replace(",", ""))
        m = comp.search(l)
        if m and pend.get(m.group(1), 0) > 0:
            pc += pend[m.group(1)]; pcn += 1; pend[m.group(1)] = 0
        m = canc.search(l)
        if m:
            pend[m.group(1)] = 0
    d["pc"] = pc; d["pcn"] = pcn
    petfirst = d["petname"].split(",")[0].strip() if d["petname"] != "-" else "Xonaner"
    killre = re.compile(r"(was|has been) slain by (Dercius|Emia|Hoggly|%s|Gekn)[!.]" % re.escape(petfirst))
    frogre = re.compile(r"Froggy (was|has been) slain")
    k = 0; frk = 0; f = None; l2 = 0
    for l in readlines("Zedus"):
        if not day_ok(l, dd):
            continue
        iskill = False
        if "You have slain " in l:
            iskill = True
        elif killre.search(l):
            iskill = True
        if iskill:
            k += 1; s = secs(l)
            if f is None or s < f:
                f = s
            if s > l2:
                l2 = s
            if "froglok" in l.lower() or "You have slain Froggy" in l or frogre.search(l):
                frk += 1
    d["kills"] = k; d["frok"] = frk
    d["hours"] = (l2 - f) / 3600.0 if f is not None else 0.0001
    ods = 0
    for t in TOONS + ["Hogga", "Discover"]:
        for l in readlines(t):
            if day_ok(l, dd) and "Death Shroud" in l and "You have looted" in l:
                ods += 1
    d["ods"] = ods
    return d


data = [(lbl, parse_day(dd)) for dd, lbl in DAYS]


def pp(x):
    return "{:,.0f}".format(x)


def fmt(x):
    return "{:,}".format(x)


rows = ""
for lbl, d in data:
    tot_dmg = sum(d["toons"][t]["total"] for t in ["Zedus", "Dercius", "Emia"]) + d["pet"]
    tot_plat = d["coin"] + d["vendor"] + d["pc"]
    rows += ("<tr><td class='day'>%s</td><td>%.1f</td><td>%s</td><td>%s</td><td>%.0f</td><td>%s</td>"
             "<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
             "<td class='tp'>%s</td><td>%s</td><td class='%s'>%d</td></tr>") % (
        lbl, d["hours"], fmt(d["kills"]), fmt(d["frok"]), d["kills"] / d["hours"], pp(tot_dmg),
        pp(d["toons"]["Emia"]["total"]), pp(d["toons"]["Dercius"]["total"]), pp(d["toons"]["Zedus"]["total"]), pp(d["pet"]),
        pp(d["coin"]), pp(d["vendor"]), pp(d["pc"]), pp(tot_plat), pp(tot_plat / d["hours"]),
        "ods1" if d["ods"] else "ods0", d["ods"])

detail = ""
for lbl, d in data:
    tot_dmg = sum(d["toons"][t]["total"] for t in ["Zedus", "Dercius", "Emia"]) + d["pet"]
    tp = d["coin"] + d["vendor"] + d["pc"]

    def toonblock(t):
        td = d["toons"][t]; sh = td["total"] / tot_dmg * 100 if tot_dmg else 0
        parts = ["melee %s" % pp(td["melee"])]
        if td["backstab"]:
            parts.append("backstab %s" % pp(td["backstab"]))
        if td["kick"]:
            parts.append("kick %s" % pp(td["kick"]))
        if td["spec"]:
            parts.append("special %s" % pp(td["spec"]))
        if td["dot"]:
            parts.append("DoT %s" % pp(td["dot"]))
        for k2, v2 in td["proc"].items():
            parts.append("%s %s" % (k2, pp(v2)))
        return "<div class='tb'><b>%s</b> — %s <span class='sh'>(%.1f%%)</span><br><span class='mv'>%s</span></div>" % (
            t, pp(td["total"]), sh, " · ".join(parts))
    detail += ("<div class='card'><h3>%s 2026</h3>"
               "<div class='kv'><span>Mobs</span><b>%s</b><span>(%s froglok)</span></div>"
               "<div class='kv'><span>Hours</span><b>%.1f</b><span>%.0f/hr</span></div>"
               "<div class='kv'><span>Damage</span><b>%s</b></div>"
               "<div class='kv'><span>Plat</span><b>%s</b><span>%s/hr</span></div>"
               "<div class='kv'><span>ODS</span><b class='%s'>%d</b></div>"
               "%s%s%s"
               "<div class='tb'><b>Pet (%s)</b> — %s</div>"
               "<div class='plat'><span>Coin %s</span><span>Vendor %s</span><span>PC sales %s (%d)</span></div></div>") % (
        lbl, fmt(d["kills"]), fmt(d["frok"]), d["hours"], d["kills"] / d["hours"], pp(tot_dmg),
        pp(tp), pp(tp / d["hours"]), "ods1" if d["ods"] else "ods0", d["ods"],
        toonblock("Emia"), toonblock("Dercius"), toonblock("Zedus"),
        d["petname"], pp(d["pet"]), pp(d["coin"]), pp(d["vendor"]), pp(d["pc"]), d["pcn"])

CSS = """
:root{--bg:#12151c;--card:#1b2029;--line:#2b3240;--txt:#e6e9ef;--dim:#8b93a3;--acc:#5fb0ff;--gold:#e8b64c;--grn:#5fd07a;--red:#e06b6b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;padding:24px}
h1{font-size:24px;margin:0 0 4px}.sub{color:var(--dim);margin-bottom:24px}
.wrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin-bottom:28px}
table{border-collapse:collapse;width:100%;min-width:1050px;font-variant-numeric:tabular-nums}
th,td{padding:9px 11px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th{background:#0e1117;color:var(--dim);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em;position:sticky;top:0}
td.day,th:first-child{text-align:left;font-weight:700;color:var(--acc)}
td.tp{font-weight:700;color:var(--gold)}.ods1{color:var(--grn);font-weight:700}.ods0{color:var(--red)}
tr:hover td{background:#20262f}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
.card h3{margin:0 0 12px;color:var(--acc);font-size:17px}
.kv{display:flex;gap:8px;align-items:baseline;margin:3px 0}.kv>span:first-child{color:var(--dim);width:70px;font-size:13px}.kv b{font-size:16px}.kv span:last-child{color:var(--dim);font-size:13px}
.tb{margin:9px 0;padding-top:9px;border-top:1px solid var(--line)}.tb .sh{color:var(--dim);font-size:13px}.mv{color:var(--dim);font-size:12.5px}
.plat{margin-top:12px;padding-top:10px;border-top:1px solid var(--line);display:flex;gap:14px;flex-wrap:wrap;color:var(--dim);font-size:13px}
.foot{color:var(--dim);font-size:12px;margin-top:24px}
"""

HEAD = ("<thead><tr><th>Day</th><th>Hrs</th><th>Kills</th><th>Frog</th><th>K/hr</th><th>Damage</th>"
        "<th>Emia</th><th>Dercius</th><th>Zedus</th><th>Pet</th><th>Coin</th><th>Vendor</th>"
        "<th>PC Sales</th><th>Total Plat</th><th>PP/hr</th><th>ODS</th></tr></thead>")

html = ("<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Sebilis Farm Log</title><style>%s</style></head><body>"
        "<h1>\U0001F438 Sebilis Farm Log</h1>"
        "<div class='sub'>Frostreaver TLP · ABC camp · comparable daily stats</div>"
        "<div class='wrap'><table>%s<tbody>%s</tbody></table></div>"
        "<div class='grid'>%s</div>"
        "<div class='foot'>Generated from EQ logs · re-run farmgen.py to add new days.</div>"
        "</body></html>") % (CSS, HEAD, rows, detail)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print("wrote", OUT, "(%d bytes)" % len(html))
for lbl, d in data:
    print("  %s: kills=%d frog=%d hrs=%.1f plat=%.0f ods=%d" % (
        lbl, d["kills"], d["frok"], d["hours"], d["coin"] + d["vendor"] + d["pc"], d["ods"]))
