"""Synthetic SOC investigation tasks (defensive) for the swarm-scaling experiment.

Each task is a fictional company's logs for one day (auth, process, DNS, proxy) containing one
planted intrusion plus benign noise and look-alike decoys. The analyst answers one question with a
single checkable answer. make_task() returns the answer to the caller only; it never writes it.
All domains, hosts and users are invented.
"""
import json, random, string
from datetime import datetime, timedelta

DAY = datetime(2026, 3, 14, 7, 0, 0)
FIRST = ["ana", "ben", "carla", "diego", "elena", "felix", "gina", "hugo", "ines", "jon", "kira",
         "luis", "mara", "nico", "olga", "pablo", "quinn", "rosa", "sam", "tina", "uma", "victor",
         "wendy", "ximena", "yuri", "zoe", "alba", "bruno", "celia", "dario", "eva", "fabio"]
LAST = ["soto", "rojas", "vidal", "munoz", "lagos", "pinto", "reyes", "silva", "fuentes", "vera",
        "nunez", "toro", "campos", "ortiz", "mora", "leon", "rios", "navarro", "paz", "cruz"]
SYL = ["lum", "tra", "vex", "nor", "qui", "zen", "dal", "ori", "kap", "sel", "mon", "fir", "bex",
       "cor", "ula", "tem", "rin", "gal", "pho", "sky", "net", "dat", "hub", "lin"]
TLD = [".com", ".net", ".io", ".co", ".info"]
FILES = {"Finance": ["Q3_payroll_export.xlsx", "vendor_bank_details.csv", "budget_2027_draft.xlsx"],
         "HR": ["employee_ssn_list.xlsx", "salary_review_2026.xlsx", "offboarding_notes.docx"],
         "Legal": ["merger_term_sheet.pdf", "litigation_hold.docx", "nda_tracker.xlsx"],
         "RnD": ["prototype_specs_v4.pdf", "patent_draft_77.docx", "roadmap_2027.pptx"]}


def dom(rng, words=2):
    return "".join(rng.choice(SYL) for _ in range(words)) + rng.choice(TLD)


def ts(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def make_task(seed: int, depth: int, noise: float = 1.0):
    rng = random.Random(seed)
    users = sorted({f"{rng.choice(FIRST)}.{rng.choice(LAST)}" for _ in range(60)})[:36]
    ws = [f"WS-{n:03d}" for n in rng.sample(range(100, 999), len(users))]
    home = dict(zip(users, ws))
    servers = ["SRV-FILE01", "SRV-DB02", "SRV-APP03", "SRV-HR04", "SRV-FIN05", "SRV-BKP06", "DC01"]
    ip = {h: f"10.{rng.randint(10, 40)}.{rng.randint(0, 9)}.{i + 10}" for i, h in enumerate(ws + servers)}
    admins = rng.sample(users, 3)
    adm_acct = {u: "adm." + u.split(".")[0] for u in admins}
    svc = ["svc_backup", "svc_sql", "svc_deploy"]
    benign_domains = [dom(rng) for _ in range(40)]
    update_dom, backup_dom, photo_dom = dom(rng), dom(rng), dom(rng)
    ev = {"auth": [], "proc": [], "dns": [], "proxy": []}

    def add(kind, t, **kw):
        ev[kind].append((t, {"time": ts(t), **kw}))

    end = DAY + timedelta(hours=13)
    # ---------------- benign background
    for u in users:
        h = home[u]; t = DAY + timedelta(minutes=rng.randint(0, 120))
        if rng.random() < 0.15:
            add("auth", t - timedelta(seconds=40), host=h, user=u, src_ip=ip[h], logon_type="interactive", result="failure")
        add("auth", t, host=h, user=u, src_ip=ip[h], logon_type="interactive", result="success")
        for p in ["outlook.exe", "chrome.exe", "teams.exe"] + (["excel.exe"] if rng.random() < .6 else []):
            add("proc", t + timedelta(minutes=rng.randint(1, 30)), host=h, user=u, process=p, parent="explorer.exe", cmdline=p)
        for _ in range(int(rng.randint(3, 8) * noise)):  # more everyday processes
            tt = t + timedelta(minutes=rng.randint(10, 600)); p = rng.choice(["excel.exe", "winword.exe", "acrord32.exe", "notepad.exe", "zoom.exe", "chrome.exe"])
            par = "outlook.exe" if p in ("winword.exe", "excel.exe", "acrord32.exe") and rng.random() < .4 else "explorer.exe"
            add("proc", tt, host=h, user=u, process=p, parent=par, cmdline=p + (f" C:\\Users\\{u}\\Documents\\notes_{rng.randint(1, 99)}.docx" if p == "winword.exe" else ""))
        for _ in range(int(rng.randint(2, 6) * noise)):  # mapped drives: benign network logons to servers
            tt = t + timedelta(minutes=rng.randint(5, 600)); s = rng.choice(["SRV-FILE01", "SRV-FILE01", "SRV-HR04", "SRV-FIN05", "SRV-APP03"])
            if rng.random() < .1:
                add("auth", tt - timedelta(seconds=15), host=s, user=u, src_ip=ip[h], logon_type="network", result="failure")
            add("auth", tt, host=s, user=u, src_ip=ip[h], logon_type="network", result="success")
        for _ in range(int(rng.randint(10, 25) * noise)):
            tt = t + timedelta(minutes=rng.randint(0, 600)); d = rng.choice(benign_domains)
            add("dns", tt, host=h, query=d, answer=f"203.0.{rng.randint(0, 255)}.{rng.randint(1, 254)}")
            add("proxy", tt + timedelta(seconds=1), host=h, user=u, method="GET", url=f"https://{d}/{rng.choice(['', 'index', 'news', 'api/feed', 'assets/app.js'])}",
                action="allowed", bytes_out=rng.randint(300, 3000), bytes_in=rng.randint(2000, 900000))
        tt = t + timedelta(minutes=rng.randint(0, 20))  # periodic update check every 15 min (benign beacon look-alike)
        while tt < end:
            add("dns", tt, host=h, query=f"check.{update_dom}", answer="198.51.100.20"); tt += timedelta(minutes=15, seconds=rng.randint(-20, 20))
        if rng.random() < 0.25:  # IT inventory script: benign powershell
            add("proc", t + timedelta(minutes=rng.randint(30, 300)), host=h, user="SYSTEM", process="powershell.exe", parent="ccmexec.exe",
                cmdline="powershell.exe -NoProfile -File C:\\IT\\inventory.ps1")
    for a in admins:  # legit admin work on servers
        for _ in range(int(rng.randint(2, 5) * noise)):
            tt = DAY + timedelta(minutes=rng.randint(60, 700)); s = rng.choice(servers)
            add("auth", tt, host=s, user=adm_acct[a], src_ip=ip[home[a]], logon_type="network", result="success")
            add("proc", tt + timedelta(minutes=2), host=s, user=adm_acct[a], process="mmc.exe", parent="explorer.exe", cmdline="mmc.exe services.msc")
    for s in servers[:-2]:  # nightly-ish backup job (archiver look-alike + big upload look-alike)
        tt = DAY + timedelta(hours=rng.choice([11, 12, 12, 13]), minutes=rng.randint(0, 59))
        add("auth", tt, host=s, user="svc_backup", src_ip=ip["SRV-BKP06"], logon_type="network", result="success")
        add("proc", tt + timedelta(minutes=1), host=s, user="svc_backup", process="archiver.exe", parent="backupagent.exe",
            cmdline=f"archiver.exe a E:\\backup\\{s.lower()}_daily.7z D:\\Shares\\")
        add("proxy", tt + timedelta(minutes=9), host=s, user="svc_backup", method="PUT", url=f"https://{backup_dom}/vault/{s.lower()}_daily.7z",
            action="allowed", bytes_out=rng.randint(200, 900) * 1_000_000, bytes_in=900)
    pu = rng.choice(users)  # personal upload decoy
    add("proxy", DAY + timedelta(minutes=rng.randint(200, 500)), host=home[pu], user=pu, method="PUT",
        url=f"https://{photo_dom}/u/{pu}/IMG_{rng.randint(1000, 9999)}.zip", action="allowed", bytes_out=rng.randint(40, 120) * 1_000_000, bytes_in=600)

    # ---------------- the intrusion
    victim = rng.choice([u for u in users if u not in admins]); H1 = home[victim]
    D1, D2, D3 = dom(rng), dom(rng, 3), dom(rng)
    decoy_victim = rng.choice([u for u in users if u not in admins + [victim]])
    t0 = DAY + timedelta(minutes=rng.randint(90, 240))
    doc = f"invoice_{rng.randint(10000, 99999)}.docm"
    add("proxy", t0 - timedelta(minutes=rng.randint(5, 40)), host=home[decoy_victim], user=decoy_victim, method="GET",
        url=f"http://{dom(rng)}/{'statement_' + str(rng.randint(100, 999))}.docm", action="blocked", bytes_out=420, bytes_in=0)
    add("dns", t0 - timedelta(seconds=2), host=H1, query=D1, answer=f"192.0.2.{rng.randint(2, 250)}")
    add("proxy", t0, host=H1, user=victim, method="GET", url=f"http://{D1}/{doc}", action="allowed", bytes_out=510, bytes_in=rng.randint(60000, 200000))
    add("proc", t0 + timedelta(minutes=1), host=H1, user=victim, process="winword.exe", parent="outlook.exe", cmdline=f"winword.exe C:\\Users\\{victim}\\Downloads\\{doc}")
    enc = "".join(rng.choice(string.ascii_letters + string.digits) for _ in range(60))
    add("proc", t0 + timedelta(minutes=1, seconds=20), host=H1, user=victim, process="powershell.exe", parent="winword.exe", cmdline=f"powershell.exe -nop -w hidden -enc {enc}")
    tb = t0 + timedelta(minutes=3)
    while tb < end:  # C2 beacon ~ every 60s with jitter
        add("dns", tb, host=H1, query=f"{rng.choice(['api', 'cdn', 'img'])}.{D2}", answer="192.0.2.77")
        if rng.random() < 0.3:
            add("proxy", tb + timedelta(seconds=1), host=H1, user=victim, method="POST", url=f"https://{D2}/api/v2/sync", action="allowed", bytes_out=rng.randint(200, 900), bytes_in=rng.randint(100, 400))
        tb += timedelta(seconds=60 + rng.randint(-8, 8))
    hard = depth >= 5
    t1 = t0 + timedelta(minutes=rng.randint(15, 50))
    add("proc", t1, host=H1, user=victim, process="svchelper.exe", parent="powershell.exe", cmdline="svchelper.exe /collect /out C:\\Users\\Public\\sv.dat")
    S1 = rng.choice(["SRV-FILE01", "SRV-HR04", "SRV-FIN05"])
    dept = {"SRV-FILE01": rng.choice(["Legal", "RnD"]), "SRV-HR04": "HR", "SRV-FIN05": "Finance"}[S1]
    A2 = rng.choice([adm_acct[rng.choice(admins)], "svc_deploy", "svc_sql"])
    t2 = t1 + timedelta(minutes=rng.randint(10, 40))
    src = H1
    if hard:  # extra hop: H1 -> S0 (account A1) -> S1 (account A2, from S0's address)
        S0 = rng.choice([s for s in ["SRV-APP03", "SRV-DB02"]]); A1 = rng.choice([a for a in ["svc_deploy", "svc_sql"] if a != A2] or ["svc_deploy"])
        for k in range(rng.randint(3, 6)):
            add("auth", t2 - timedelta(seconds=30 * (k + 1)), host=S0, user=rng.choice(list(adm_acct.values()) + svc), src_ip=ip[H1], logon_type="network", result="failure")
        add("auth", t2, host=S0, user=A1, src_ip=ip[H1], logon_type="network", result="success")
        add("proc", t2 + timedelta(minutes=2), host=S0, user=A1, process="svchelper.exe", parent="cmd.exe", cmdline="svchelper.exe /collect /out C:\\Windows\\Temp\\s.dat")
        t2 = t2 + timedelta(minutes=rng.randint(10, 30)); src = S0
    for k in range(rng.randint(2, 5)):  # failed logons with other accounts first
        add("auth", t2 - timedelta(seconds=30 * (k + 1)), host=S1, user=rng.choice(list(adm_acct.values()) + svc), src_ip=ip[src], logon_type="network", result="failure")
    add("auth", t2, host=S1, user=A2, src_ip=ip[src], logon_type="network", result="success")
    fname = rng.choice(FILES[dept]); arch = "".join(rng.choice(string.ascii_lowercase) for _ in range(6))
    t3 = t2 + timedelta(minutes=rng.randint(5, 25))
    if not hard:
        add("proc", t3, host=S1, user=A2, process="archiver.exe", parent="cmd.exe", cmdline=f"archiver.exe a -p C:\\ProgramData\\tmp\\{arch}.7z D:\\Shares\\{dept}\\{fname}")
        t4 = t3 + timedelta(minutes=rng.randint(5, 25))
        add("dns", t4 - timedelta(seconds=1), host=S1, query=f"files.{D3}", answer=f"192.0.2.{rng.randint(2, 250)}")
        add("proxy", t4, host=S1, user=A2, method="PUT", url=f"https://files.{D3}/upload/{arch}.7z", action="allowed", bytes_out=rng.randint(30, 150) * 1_000_000, bytes_in=700)
    else:
        # two files copied to renamed temp files, both archived; one archive deleted; the other leaves via DNS tunnelling
        others = rng.sample([f for f in FILES[dept] if f != fname], 2 if depth >= 7 else 1)
        rnd_name = lambda: "".join(rng.choice(string.ascii_lowercase) for _ in range(6))
        staged = [(fname, f"{rng.randint(100, 999)}.tmp", arch)] + [(o, f"{rng.randint(100, 999)}.tmp", rnd_name()) for o in others]
        order_st = staged[:]; rng.shuffle(order_st)
        tt = t3
        for orig, tmpn, an in order_st:
            add("proc", tt, host=S1, user=A2, process="cmd.exe", parent="cmd.exe", cmdline=f"cmd.exe /c copy D:\\Shares\\{dept}\\{orig} C:\\ProgramData\\tmp\\{tmpn}")
            add("proc", tt + timedelta(minutes=1), host=S1, user=A2, process="archiver.exe", parent="cmd.exe", cmdline=f"archiver.exe a -p C:\\ProgramData\\tmp\\{an}.7z C:\\ProgramData\\tmp\\{tmpn}")
            tt += timedelta(minutes=rng.randint(2, 6))
        add("proc", tt, host=S1, user=A2, process="cmd.exe", parent="cmd.exe", cmdline=f"cmd.exe /c del C:\\ProgramData\\tmp\\{staged[-1][2]}.7z")
        t4 = tt + timedelta(minutes=rng.randint(5, 20))

        def tunnel(archive, domain, start, key, sinkholed, job):
            raw = f"{archive}.7z".encode() + bytes(rng.randrange(256) for _ in range(rng.randint(130, 210)))
            if key is not None:  # tunnel tool XORs the stream with a one-byte key given on its command line
                add("proc", start - timedelta(seconds=40), host=S1, user=A2, process="dnsup.exe", parent="cmd.exe",
                    cmdline=f"dnsup.exe -k 0x{key:02x} -j C:\\ProgramData\\tmp\\{job}.cfg")
                raw = bytes(b ^ key for b in raw)
            hx = raw.hex(); chunks = [hx[i:i + 30] for i in range(0, len(hx), 30)]
            order = list(range(len(chunks))); rng.shuffle(order)
            for j, ci in enumerate(order):  # sequence number + hex chunk; sent out of order
                rec = dict(host=S1, query=f"{ci:03d}{chunks[ci]}.t.{domain}", answer="0.0.0.0")
                if depth >= 7: rec["action"] = "sinkholed" if sinkholed else "allowed"
                add("dns", start + timedelta(seconds=3 * j), **rec)

        if depth >= 7:  # two tunnels: the real one (allowed) and one to another domain that the DNS filter sinkholed
            D4 = dom(rng); jobs = rng.sample(["j1", "j2", "j7", "q3"], 2)
            ka, kb = rng.sample(range(17, 250), 2)
            first_real = rng.random() < 0.5
            tunnel(arch if first_real else staged[1][2], D3 if first_real else D4, t4, ka, not first_real, jobs[0])
            tunnel(staged[1][2] if first_real else arch, D4 if first_real else D3, t4 + timedelta(minutes=rng.randint(4, 12)), kb, first_real, jobs[1])
        else:
            tunnel(arch, D3, t4, None, False, None)
        # benign look-alike: CDN with long hashed subdomains on many hosts
        cdn = dom(rng)
        for _ in range(int(40 * noise)):
            h = rng.choice(ws + servers[:3])
            add("dns", DAY + timedelta(minutes=rng.randint(0, 700)), host=h, query=f"{''.join(rng.choice('0123456789abcdef') for _ in range(32))}.edge.{cdn}", answer="198.51.100.9")
    infected = [H1]
    if depth >= 6:  # attacker spreads to a second workstation with the victim's account; it beacons to another subdomain
        v2 = rng.choice([u for u in users if u not in admins + [victim, decoy_victim]]); H2 = home[v2]
        tl = t1 + timedelta(minutes=rng.randint(3, 9))
        add("auth", tl, host=H2, user=victim, src_ip=ip[H1], logon_type="network", result="success")
        add("proc", tl + timedelta(seconds=30), host=H2, user="SYSTEM", process="updsvc.exe", parent="services.exe", cmdline="updsvc.exe -k netsvcs")
        tb = tl + timedelta(minutes=2)
        while tb < end:
            add("dns", tb, host=H2, query=f"{rng.choice(['m', 'static'])}.{D2}", answer="192.0.2.78"); tb += timedelta(seconds=90 + rng.randint(-10, 10))
        infected.append(H2)

    # ---------------- question
    Q = {
        1: ("Which external domain hosted the malicious document that started the intrusion?", "domain (e.g. example.com)", D1),
        2: ("Which account did the attacker use for the first successful logon to a server from the initially compromised workstation?", "account name", A2),
        3: ("Which file was exfiltrated (original file name, not the archive), and to which domain was it uploaded? Give the registrable domain without subdomains.", "filename|domain", f"{fname}|{D3}"),
        4: ("Give the hostname of the first compromised workstation, the command-and-control domain it beaconed to (registrable domain, no subdomain), and the server where data was staged for exfiltration.",
            "host|c2domain|server", f"{H1}|{D2}|{S1}"),
        5: ("Which file was exfiltrated (its original file name on the share, not any temporary or archive name), which account did the attacker use on the server it was taken from, and to which domain was it exfiltrated (registrable domain, no subdomain)?",
            "filename|account|domain", f"{fname}|{A2}|{D3}"),
        6: ("List every workstation that communicated with the attacker's command-and-control domain (comma-separated), the original file name of the file that was exfiltrated (not any temporary or archive name), and the domain it was exfiltrated to (registrable domain, no subdomain).",
            "host1,host2,...|filename|domain", f"{','.join(sorted(infected))}|{fname}|{D3}"),
        7: ("List every workstation that communicated with the attacker's command-and-control domain (comma-separated), the account the attacker used on the server the data was taken from, "
            "the original file name of the file that actually left the network (not any temporary or archive name), and the domain it was exfiltrated to (registrable domain, no subdomain).",
            "host1,host2,...|account|filename|domain", f"{','.join(sorted(infected))}|{A2}|{fname}|{D3}"),
    }[depth]
    files = {}
    names = {"auth": "auth.jsonl", "proc": "process.jsonl", "dns": "dns.jsonl", "proxy": "proxy.jsonl"}
    for k, lst in ev.items():
        lst.sort(key=lambda x: x[0])
        files[names[k]] = "\n".join(json.dumps(r) for _, r in lst) + "\n"
    q = (f"# Incident investigation\n\nThe SOC received an alert about suspicious activity at a company on 2026-03-14 (all times UTC).\n"
         f"Logs for that day are in this directory: {', '.join(sorted(files))} (one JSON object per line).\n"
         f"The logs contain normal activity and look-alike benign events; base your answer on evidence.\n\n"
         f"**Question:** {Q[0]}\n\n**Answer format:** `{Q[1]}`\n")
    files["QUESTION.md"] = q
    return files, Q[0], Q[1], Q[2]


def normalize(s: str) -> str:
    s = s.strip().strip("`").strip().lower()
    return "|".join(",".join(sorted(x.strip() for x in p.split(","))) for p in s.split("|"))


if __name__ == "__main__":  # quick self-check: sizes only, never print the answer
    f, q, fmt, a = make_task(1, 4)
    print(q, fmt, {k: v.count("\n") for k, v in f.items()})
