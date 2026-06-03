#!/usr/bin/env python3
"""Refresh the knowledge base from sources.yaml.

Usage:
  uv run --with pyyaml python update.py            # refresh everything
  uv run --with pyyaml python update.py NAME ...   # refresh only named sources
  uv run --with pyyaml python update.py --list     # list sources and exit

Resumable: safe to cancel and re-run. Only new / changed content is fetched
(wget -N skips unchanged pages, git fast-forwards, PDFs are timestamp-checked).
Each run prints a change report and appends to _UPDATE_LOG.md.
"""
import sys, os, re, subprocess, hashlib, datetime
import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


# ---------- change detection ----------
def sha1_file(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()

def snapshot(path):
    snap = {}
    if os.path.isfile(path):
        snap[os.path.basename(path)] = sha1_file(path)
    elif os.path.isdir(path):
        for dp, dirs, files in os.walk(path):
            if ".git" in dp.split(os.sep):
                continue
            for fn in files:
                fp = os.path.join(dp, fn)
                try:
                    snap[os.path.relpath(fp, path)] = sha1_file(fp)
                except OSError:
                    pass
    return snap

def diff_snaps(before, after):
    b, a = set(before), set(after)
    added = sorted(a - b)
    removed = sorted(b - a)
    modified = sorted(k for k in (a & b) if before[k] != after[k])
    return added, modified, removed


# ---------- helpers ----------
def run(cmd):
    print("   $", " ".join(cmd))
    return subprocess.run(cmd)

def curl_text(url):
    r = subprocess.run(["curl", "-fsSL", "-A", UA, url],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


# ---------- fetchers (return (ok: bool, note: str)) ----------
def fetch_pdf(s):
    dest = os.path.join(ROOT, s["dest"])
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    url = s.get("url")
    if s.get("url_page") and s.get("url_regex"):
        page = curl_text(s["url_page"])
        m = re.search(s["url_regex"], page)
        if not m:
            return False, "could not discover URL from page (regex no match)"
        url = m.group(0)
        print("   discovered:", url)
    if not url:
        return False, "no url"
    cmd = ["curl", "-fsSL", "--remote-time", "-A", UA, "-o", dest]
    if os.path.exists(dest):
        cmd += ["-z", dest]          # only download if remote is newer
    cmd += [url]
    return (run(cmd).returncode == 0), url

def fetch_wget(s):
    dest = os.path.join(ROOT, s["dest"])
    os.makedirs(dest, exist_ok=True)
    cmd = ["wget", "-r", "-N", "-l", "inf", "-np", "-E", "-e", "robots=off",
           "--tries=3", "--timeout=30", "--wait=0.3", "--random-wait", "-nv",
           "-U", UA, "-P", dest]
    if s.get("domains"):
        cmd += ["-D", s["domains"]]
    if s.get("include_dirs"):
        cmd += ["--include-directories=" + s["include_dirs"]]
    cmd += list(s.get("urls") or [s["url"]])
    rc = run(cmd).returncode
    return rc in (0, 8), ""          # 8 = some pages 404'd; mirror still valid

def git_head(dest):
    r = subprocess.run(["git", "-C", dest, "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "?"

def fetch_git(s):
    dest = os.path.join(ROOT, s["dest"])
    if os.path.isdir(os.path.join(dest, ".git")):
        before = git_head(dest)
        run(["git", "-C", dest, "fetch", "--depth", "1", "origin"])
        rc = run(["git", "-C", dest, "reset", "--hard", "FETCH_HEAD"]).returncode
        after = git_head(dest)
        return rc == 0, ("unchanged @ " + after if before == after
                         else f"{before} -> {after}")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    rc = run(["git", "clone", "--depth", "1", s["url"], dest]).returncode
    return rc == 0, ("cloned @ " + git_head(dest) if rc == 0 else "clone failed")


# ---------- main ----------
def main(argv):
    with open(os.path.join(ROOT, "sources.yaml")) as f:
        sources = yaml.safe_load(f)["sources"]

    if "--list" in argv:
        for s in sources:
            print(f"  {s['name']:<34} {s['type']:<7} -> {s['dest']}")
        return 0

    wanted = [a for a in argv if not a.startswith("-")]
    if wanted:
        sources = [s for s in sources if s["name"] in wanted]
        missing = set(wanted) - {s["name"] for s in sources}
        if missing:
            print("unknown source(s):", ", ".join(sorted(missing)))
            return 2

    results = []
    for s in sources:
        name, typ = s["name"], s["type"]
        dest = os.path.join(ROOT, s["dest"])
        print(f"\n=== {name}  ({typ}) ===")

        if typ == "static":
            results.append((name, "static", "vendored — not fetched", ""))
            print("   vendored static asset; skipping.")
            continue
        if typ == "gated":
            results.append((name, "GATED", "needs manual download", ""))
            print("   !! GATED:", (s.get("note") or "").strip())
            print("   landing:", s.get("landing", "?"))
            continue

        use_snap = typ in ("pdf", "wget")
        before = snapshot(dest) if use_snap else {}
        try:
            if typ == "pdf":
                ok, info = fetch_pdf(s)
            elif typ == "wget":
                ok, info = fetch_wget(s)
            elif typ == "git":
                ok, info = fetch_git(s)
            else:
                ok, info = False, f"unknown type {typ}"
        except Exception as e:  # surface, never swallow
            ok, info = False, f"EXCEPTION: {e}"

        if use_snap:
            a, m, r = diff_snaps(before, snapshot(dest))
            change = f"+{len(a)} ~{len(m)} -{len(r)} files"
        else:
            change = info
        status = "ok" if ok else "FAILED"
        results.append((name, status, change, info if use_snap else ""))
        print(f"   {status}: {change}")

    # ---- summary + log ----
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"\n## Update {stamp}", ""]
    print("\n" + "=" * 60 + "\nSUMMARY")
    for name, status, change, _ in results:
        row = f"  {status:<7} {name:<34} {change}"
        print(row)
        lines.append(f"- **{status}** `{name}` — {change}")
    with open(os.path.join(ROOT, "_UPDATE_LOG.md"), "a") as f:
        f.write("\n".join(lines) + "\n")

    failed = [n for n, st, *_ in results if st == "FAILED"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
