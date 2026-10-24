"""Build the friends' pack: the cobblemon pack as a Modrinth .mrpack, for players who
don't run sync.ps1 (Mac users, or anyone without Claude). They import it into the
Modrinth App. Settings live in packs/cobblemon/friends/pack.json.

    python -I tools/build-friends-pack.py             # build dist/<asset>
    python -I tools/build-friends-pack.py --upload    # build, then replace the asset on the
                                                      # GitHub release (needs gh, logged in)

The .mrpack lists download URLs and hashes; it doesn't contain any mod files. It adds:
options.txt (the host's key layout, texture packs switched on), servers.dat (the
server in the Multiplayer list), the pack's config_files, and friends/overrides/.
"""
import argparse, hashlib, io, json, pathlib, struct, subprocess, sys, tempfile, time, urllib.request, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PACK = ROOT / "packs" / "cobblemon"
FRIENDS = PACK / "friends"
UA = {"User-Agent": "av1017/minecraft-modpack build-friends-pack"}


def fetch(url, data=None):
    headers = dict(UA)
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    return urllib.request.urlopen(req, timeout=120).read()


def nbt_servers(servers):
    """servers.dat: an uncompressed NBT compound holding a list of {name, ip}."""
    def s(text):
        b = text.encode("utf-8")
        return struct.pack(">H", len(b)) + b
    out = b"\x0a" + s("") + b"\x09" + s("servers") + b"\x0a" + struct.pack(">i", len(servers))
    for srv in servers:
        out += b"\x08" + s("name") + s(srv["name"]) + b"\x08" + s("ip") + s(srv["ip"]) + b"\x00"
    return out + b"\x00"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upload", action="store_true")
    a = ap.parse_args()

    m = json.loads((PACK / "mods.json").read_text(encoding="utf-8"))
    cfg = json.loads((FRIENDS / "pack.json").read_text(encoding="utf-8"))

    entries = []   # (path, manifest entry, env)
    for x in m["mods"]:
        if x["slug"] in cfg["exclude"]:
            continue
        env = {"client": "required", "server": "required" if x.get("side") == "both" else "unsupported"}
        entries.append(("mods/" + x["filename"], x, env))
    for x in m.get("resourcepacks", []):
        entries.append(("resourcepacks/" + x["filename"], x, {"client": "required", "server": "unsupported"}))
    for x in m.get("shaderpacks", []):
        entries.append(("shaderpacks/" + x["filename"], x, {"client": "required", "server": "unsupported"}))

    # sha512 and size: Modrinth's API knows them for its own files; download the rest.
    hashes = [x["sha1"] for _, x, _ in entries]
    known = json.loads(fetch("https://api.modrinth.com/v2/version_files",
                             json.dumps({"hashes": hashes, "algorithm": "sha1"}).encode()))
    files = []
    for path, x, env in entries:
        info = None
        for f in known.get(x["sha1"], {}).get("files", []):
            if f["hashes"]["sha1"] == x["sha1"]:
                info = (f["hashes"]["sha512"], f["size"])
        if info is None:
            blob = fetch(x["url"])
            if hashlib.sha1(blob).hexdigest() != x["sha1"]:
                sys.exit(f"SHA-1 mismatch downloading {x['filename']}; nothing built.")
            info = (hashlib.sha512(blob).hexdigest(), len(blob))
            print(f"  hashed {x['filename']} (not on Modrinth)")
        files.append({"path": path, "hashes": {"sha1": x["sha1"], "sha512": info[0]},
                      "env": env, "downloads": [x["url"]], "fileSize": info[1]})

    # options.txt: only the lines we care about; Minecraft fills in its defaults for the rest.
    packs = ["vanilla", "fabric"] + cfg["builtin_resourcepacks"]
    packs += ["file/" + x["filename"] for x in m.get("resourcepacks", []) if x.get("enabled", True)]
    options = [f"version:{cfg['data_version']}",
               "resourcePacks:" + json.dumps(packs, ensure_ascii=False, separators=(",", ":"))]
    if m.get("key_layout"):   # the host's full key bindings, so friends' controls match
        options += [l.strip() for l in (ROOT / m["key_layout"]["source"]).read_text(encoding="utf-8").splitlines() if l.startswith("key_")]
    else:
        options += [f"{k['key']}:{k['to']}" for k in m.get("keybinds", [])]

    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip() or "local"
    version = time.strftime("%Y.%m.%d") + "-" + commit
    index = {"formatVersion": 1, "game": "minecraft", "versionId": version, "name": cfg["name"],
             "summary": cfg["summary"], "files": files,
             "dependencies": {"minecraft": m["minecraft"], "fabric-loader": m["loader"]["version"]}}

    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    out = dist / cfg["asset"]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("modrinth.index.json", json.dumps(index, ensure_ascii=False, indent=2))
        z.writestr("overrides/options.txt", "\n".join(options) + "\n")
        z.writestr("overrides/servers.dat", nbt_servers(cfg["servers"]))
        for c in m.get("config_files", []):
            z.write(ROOT / c["source"], "overrides/" + c["file"])
        for p in sorted((FRIENDS / "overrides").rglob("*")):
            if p.is_file():
                z.write(p, "overrides/" + p.relative_to(FRIENDS / "overrides").as_posix())
    print(f"built {out} ({out.stat().st_size // 1024} KB): {len(files)} files, version {version}")

    if a.upload:
        tag = cfg["release_tag"]
        notes = (f"Pack version {version}. Download {cfg['asset']} and import it into the Modrinth App. "
                 "Steps: https://av1017.github.io/minecraft-modpack/#online")
        exists = subprocess.run(["gh", "release", "view", tag], cwd=ROOT, capture_output=True).returncode == 0
        if exists:
            subprocess.run(["gh", "release", "upload", tag, str(out), "--clobber"], cwd=ROOT, check=True)
            subprocess.run(["gh", "release", "edit", tag, "--notes", notes], cwd=ROOT, check=True)
        else:
            subprocess.run(["gh", "release", "create", tag, str(out), "--title", "Friends' pack (Modrinth App)",
                            "--notes", notes, "--latest=false"], cwd=ROOT, check=True)
        print(f"uploaded: https://github.com/av1017/minecraft-modpack/releases/download/{tag}/{cfg['asset']}")


if __name__ == "__main__":
    main()
