import os, re
LOGDIR = r"C:/Users/Public/Daybreak Game Company/Installed Games/EverQuest/Logs"
OUT = r"C:/Users/Dercius/Desktop/EQFarmLog/index.html"
TOONS = ["Zedus", "Dercius", "Emia", "Hoggly"]
VENDOR_TOONS = ["Hogga", "Shoppe"]      # NPC-vendor sellers
PC_TOONS = ["Discover", "Shoppe"]       # player-trade sellers (Shoppe treated like Discover too)
GROUP = set(["Zedus", "Dercius", "Emia", "Hoggly", "Thrice", "Loriex", "Hogga", "Discover", "Shoppe", "Froggy"])
COINWORDS = ("platinum", "gold", "silver", "copper")


def readlines(name):
    p = os.path.join(LOGDIR, "eqlog_%s_frostreaver.txt" % name)
    if not os.path.exists(p):
        return []
    with open(p, "rb") as f:
        raw = f.read()
    return raw.decode("latin-1").split("\n")


MONTH_ORD = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
CUR = {"mo": "Jul", "yr": "2026"}


def day_ok(line, dd):
    return len(line) > 25 and line[5:8] == CUR["mo"] and line[9:11] == dd and line[21:25] == CUR["yr"]


def detect_days():
    seen = {}
    for l in readlines("Zedus"):
        if len(l) < 25:
            continue
        mo, dd, yr = l[5:8], l[9:11], l[21:25]
        if mo in MONTH_ORD and yr.isdigit() and "slain" in l:
            seen[(yr, mo, dd)] = seen.get((yr, mo, dd), 0) + 1
    days = [k for k, c in seen.items() if c > 20]  # only days with real farming (>20 kills)
    days.sort(key=lambda k: (int(k[0]), MONTH_ORD[k[1]], int(k[2])))
    return [(mo, dd, yr, "%s %d" % (mo, int(dd))) for (yr, mo, dd) in days]


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
re_off = re.compile(r"([A-Za-z]+) has offered you ([0-9,]+) platinum")
re_gave = re.compile(r"You offered \d+ (.+?) to ([A-Za-z]+)\.")
re_comp = re.compile(r"You complete the trade with ([A-Za-z]+)")
re_canc = re.compile(r"([A-Za-z]+) has cancelled the trade")


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


def parse_day(mo, dd, yr):
    CUR["mo"] = mo; CUR["yr"] = yr
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
                td["spec"] += int(m.group(1)); td["total"] += int(m.group(1)); continue
            m = re_dot.search(l)
            if m:
                td["dot"] += int(m.group(1)); td["total"] += int(m.group(1)); continue
            m = re_proc.search(l)
            if m:
                n = int(m.group(1)); pr = m.group(2)
                td["proc"][pr] = td["proc"].get(pr, 0) + n; td["total"] += n; continue
        d["toons"][t] = td
    petdmg = 0
    if pets:
        petre = re.compile(r"\] (?:%s) .* for (\d+) point" % ("|".join(pets)))
        for l in readlines("Hoggly"):
            if day_ok(l, dd):
                m = petre.search(l)
                if m:
                    petdmg += int(m.group(1))
    d["pet"] = petdmg
    d["petname"] = ", ".join(pets) if pets else "-"
    # coin
    coin = 0.0
    for t in TOONS:
        for l in readlines(t):
            if day_ok(l, dd) and re_coin.search(l):
                coin += coinval(l)
    d["coin"] = coin
    # vendor sales (Hogga + Shoppe) with per-item breakdown
    vitems = {}
    vtot = 0.0
    for t in VENDOR_TOONS:
        for l in readlines(t):
            if day_ok(l, dd) and " for the " in l and "You receive" in l:
                val = coinval(l)
                item = l.split(" for the ", 1)[1].strip()
                item = item.replace("(s).", "").replace("(s)", "").rstrip(".").strip()
                e = vitems.setdefault(item, [0, 0.0])
                e[0] += 1; e[1] += val; vtot += val
    d["vendor"] = vtot
    d["vitems"] = sorted(vitems.items(), key=lambda x: -x[1][1])
    # PC sales (Discover + Shoppe) with per-item breakdown
    pitems = []; ptot = 0.0; pcn = 0
    for t in PC_TOONS:
        pend_item = {}; pend_plat = {}
        for l in readlines(t):
            if not day_ok(l, dd):
                continue
            m = re_gave.search(l)
            if m and m.group(1) not in COINWORDS:
                pend_item.setdefault(m.group(2), []).append(m.group(1))
            m = re_off.search(l)
            if m:
                pend_plat[m.group(1)] = float(m.group(2).replace(",", ""))
            m = re_comp.search(l)
            if m:
                p = m.group(1); plat = pend_plat.get(p, 0)
                if plat > 0:
                    itm = ", ".join(pend_item.get(p, [])) or "(item)"
                    pitems.append((itm, plat, p)); ptot += plat; pcn += 1
                pend_plat[p] = 0; pend_item[p] = []
            m = re_canc.search(l)
            if m:
                pend_plat[m.group(1)] = 0; pend_item[m.group(1)] = []
    d["pc"] = ptot; d["pcn"] = pcn
    d["pitems"] = sorted(pitems, key=lambda x: -x[1])
    # kills + froglok + span
    petfirst = d["petname"].split(",")[0].strip() if d["petname"] != "-" else "Xonaner"
    killre = re.compile(r"(was|has been) slain by (Dercius|Emia|Hoggly|%s|Gekn)[!.]" % re.escape(petfirst))
    frogre = re.compile(r"Froggy (was|has been) slain")
    k = 0; frk = 0; f = None; l2 = 0
    for l in readlines("Zedus"):
        if not day_ok(l, dd):
            continue
        iskill = "You have slain " in l or killre.search(l)
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
    for t in TOONS + VENDOR_TOONS + ["Discover"]:
        for l in readlines(t):
            if day_ok(l, dd) and "Death Shroud" in l and "You have looted" in l:
                ods += 1
    d["ods"] = ods
    return d


DAYS = detect_days()
data = [(lbl, parse_day(mo, dd, yr)) for mo, dd, yr, lbl in DAYS]


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

    vlist = "".join("<li><span>%s <em>x%d</em></span><span class='amt'>%s</span></li>" % (it, c[0], pp(c[1]))
                    for it, c in d["vitems"]) or "<li class='none'>none</li>"
    plist = "".join("<li><span>%s</span><span class='amt'>%s <em>%s</em></span></li>" % (it, pp(plat), who)
                    for it, plat, who in d["pitems"]) or "<li class='none'>none</li>"

    detail += ("<div class='card'><h3>%s 2026</h3>"
               "<div class='kv'><span>Mobs</span><b>%s</b><span>(%s froglok)</span></div>"
               "<div class='kv'><span>Hours</span><b>%.1f</b><span>%.0f/hr</span></div>"
               "<div class='kv'><span>Damage</span><b>%s</b></div>"
               "<div class='kv'><span>Plat</span><b>%s</b><span>%s/hr</span></div>"
               "<div class='kv'><span>ODS</span><b class='%s'>%d</b></div>"
               "%s%s%s"
               "<div class='tb'><b>Pet (%s)</b> — %s <span class='sh'>(%.1f%%)</span></div>"
               "<div class='plat'><span>Coin %s</span><span>Vendor %s</span><span>PC sales %s (%d)</span></div>"
               "<details class='det'><summary>Vendored items (%s pp)</summary><ul class='il'>%s</ul></details>"
               "<details class='det'><summary>PC sales (%s pp)</summary><ul class='il'>%s</ul></details>"
               "</div>") % (
        lbl, fmt(d["kills"]), fmt(d["frok"]), d["hours"], d["kills"] / d["hours"], pp(tot_dmg),
        pp(tp), pp(tp / d["hours"]), "ods1" if d["ods"] else "ods0", d["ods"],
        toonblock("Emia"), toonblock("Dercius"), toonblock("Zedus"),
        d["petname"], pp(d["pet"]), (d["pet"] / tot_dmg * 100 if tot_dmg else 0), pp(d["coin"]), pp(d["vendor"]), pp(d["pc"]), d["pcn"],
        pp(d["vendor"]), vlist, pp(d["pc"]), plist)

CSS = """
:root{--bg:#12151c;--card:#1b2029;--line:#2b3240;--txt:#e6e9ef;--dim:#8b93a3;--acc:#5fb0ff;--gold:#e8b64c;--grn:#5fd07a;--red:#e06b6b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;padding:24px}
h1{font-size:24px;margin:0 0 4px}.sub{color:var(--dim);margin-bottom:16px}
.nav{margin-bottom:24px}.nav a{display:inline-block;color:var(--acc);text-decoration:none;border:1px solid var(--line);padding:7px 13px;border-radius:7px;font-size:14px;background:var(--card)}.nav a:hover{background:#20262f;border-color:var(--acc)}
.rbtn{background:var(--grn);color:#0e1117;border:none;padding:8px 15px;border-radius:7px;font-size:14px;font-weight:700;cursor:pointer;margin-left:10px}.rbtn:hover{filter:brightness(1.08)}.rbtn:disabled{opacity:.6;cursor:wait}
.wrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin-bottom:28px}
table{border-collapse:collapse;width:100%;min-width:1050px;font-variant-numeric:tabular-nums}
th,td{padding:9px 11px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th{background:#0e1117;color:var(--dim);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em;position:sticky;top:0}
td.day,th:first-child{text-align:left;font-weight:700;color:var(--acc)}
td.tp{font-weight:700;color:var(--gold)}.ods1{color:var(--grn);font-weight:700}.ods0{color:var(--red)}
tr:hover td{background:#20262f}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
.card h3{margin:0 0 12px;color:var(--acc);font-size:17px}
.kv{display:flex;gap:8px;align-items:baseline;margin:3px 0}.kv>span:first-child{color:var(--dim);width:70px;font-size:13px}.kv b{font-size:16px}.kv span:last-child{color:var(--dim);font-size:13px}
.tb{margin:9px 0;padding-top:9px;border-top:1px solid var(--line)}.tb .sh{color:var(--dim);font-size:13px}.mv{color:var(--dim);font-size:12.5px}
.plat{margin-top:12px;padding-top:10px;border-top:1px solid var(--line);display:flex;gap:14px;flex-wrap:wrap;color:var(--dim);font-size:13px}
.det{margin-top:10px;border-top:1px solid var(--line);padding-top:8px}.det summary{cursor:pointer;color:var(--gold);font-size:13px;font-weight:600}
.il{list-style:none;margin:8px 0 0;padding:0;max-height:260px;overflow-y:auto;font-variant-numeric:tabular-nums}
.il li{display:flex;justify-content:space-between;gap:10px;padding:3px 0;font-size:13px;border-bottom:1px solid #232a34}
.il li span:first-child{color:var(--txt)}.il em{color:var(--dim);font-style:normal;font-size:12px}
.il .amt{color:var(--gold);white-space:nowrap}.il .none{color:var(--dim);justify-content:flex-start}
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
        "<div class='nav'><a href='eq-bard-guide-tov.html'>\U0001F3B5 Bard — Temple of Veeshan Guide &rarr;</a>"
        "<button id='refresh' class='rbtn' onclick='doRefresh()'>\U0001F504 Refresh Data</button></div>"
        "<div class='wrap'><table>%s<tbody>%s</tbody></table></div>"
        "<div class='grid'>%s</div>"
        "<div class='foot'>Generated from EQ logs · vendor = Hogga+Shoppe · PC sales = Discover+Shoppe · re-run farmgen.py to update.</div>"
        "<script>"
        "function doRefresh(){var b=document.getElementById('refresh');b.textContent='Refreshing... (~2 min)';b.disabled=true;"
        "fetch('/refresh').then(function(r){return r.text();}).then(function(){location.reload();})"
        ".catch(function(){b.textContent='\U0001F504 Refresh Data';b.disabled=false;"
        "alert('The Refresh button only works when the page is opened via start.bat (the local server) - not on the GitHub-hosted version.');});}"
        "var h=location.hostname;if(h!=='localhost'&&h!=='127.0.0.1'){var el=document.getElementById('refresh');if(el)el.style.display='none';}"
        "</script>"
        "</body></html>") % (CSS, HEAD, rows, detail)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print("wrote", OUT, "(%d bytes)" % len(html))
for lbl, d in data:
    print("  %s: kills=%d plat=%.0f (coin %.0f / vend %.0f [%d items] / pc %.0f [%d trades]) ods=%d" % (
        lbl, d["kills"], d["coin"] + d["vendor"] + d["pc"], d["coin"], d["vendor"], len(d["vitems"]),
        d["pc"], d["pcn"], d["ods"]))

# auto-commit + push to GitHub so the hosted page updates
import subprocess, datetime
R = os.path.dirname(OUT)
try:
    subprocess.run(["git", "-C", R, "add", "-A"], check=False)
    msg = "Update farm log " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    subprocess.run(["git", "-C", R, "-c", "user.name=buzzimij",
                    "-c", "user.email=michaeljbuzzi@gmail.com", "commit", "-m", msg], check=False)
    subprocess.run(["git", "-C", R, "push"], check=False)
    print("pushed to GitHub (buzzimij/eq-farm-log)")
except Exception as e:
    print("git push skipped:", e)
