"""Generates the Cobble Valley parts of the guide from the Cobble Valley Ages mod's real data.
Run from the modpack folder:  python -I tools/pages/gen_cobblevalley.py [path/to/cobble-valley-ages]

1. Snapshot: copies the mod's data (dump, gear list, books, quests, ages, disciplines, tuning, crate loot,
   chest table) into data/cvages/ so the site can be regenerated without the mod folder. With no mod folder
   (or it's missing), the existing snapshot is used.
2. Fragments: writes tools/pages/generated/*.html, which the Cobble Valley and Dev page bodies include
   (build.py replaces <!-- include: generated/x.html --> with the file).
3. Boxes: writes an "In Cobble Valley" box into every existing guide page in docs/, between
   <!-- cv-box --> and <!-- /cv-box --> markers (inserted before the page's jump menu or first section the
   first time). Edit PAGES below to change what a page's box says.

Then run tools/pages/make.py (or build.py for single pages). Never hand-edit generated files."""
import csv
import glob
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SNAP = os.path.join(ROOT, "data", "cvages")
GEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated")
DOCS = os.path.join(ROOT, "docs")
DEFAULT_MOD = os.path.join(ROOT, "..", "cobble-valley-ages")

MOD_NAMES = {
    "minecraft": "Vanilla", "cobblemon": "Cobblemon", "mcwfurnitures": "Macaw's Furniture", "magistuarmory": "Epic Knights",
    "cobblefurnies": "CobbleFurnies", "cobbreeding": "Cobbreeding", "mcwwindows": "Macaw's Windows", "simplehats": "Simple Hats",
    "mega_showdown": "Mega Showdown", "handcrafted": "Handcrafted", "supplementaries": "Supplementaries", "mca": "MCA Reborn",
    "farmersdelight": "Farmer's Delight", "botanypots": "Botany Pots", "another_furniture": "Another Furniture",
    "storagedelight": "Storage Delight", "rusticdelight": "Rustic Delight", "weaversparadise": "Weaver's Paradise",
    "mcwlights": "Macaw's Lights", "poke-clothing": "Poke Clothing", "smallships": "Small Ships", "travelersbackpack": "Traveler's Backpack",
    "cobblemonpokemonbadges": "Pokémon Badges", "beautify": "Beautify", "cobblemonarmors": "Cobblemon Armors",
    "immersive_armors": "Immersive Armors", "ricksportalgun": "Rick's Portal Gun", "immersive_aircraft": "Immersive Aircraft",
    "pokebike": "PokeBike", "automobility": "Automobility", "rctmod": "Radical Cobblemon Trainers", "moonlight": "Moonlight Lib",
    "twinportals": "Twin Portals", "patchouli": "Patchouli", "leaf_beds": "Leaf Beds", "cvages": "Cobble Valley Ages",
}
CATEGORY_NAMES = {"NONE": "", "TOOL": "Tool", "MELEE": "Weapon", "ARMOR": "Armor", "RANGED": "Ranged", "SHIELD": "Shield"}
POLICY_CODES = {"AUTO": "A", "MUST_LEARN": "M", "BOOK": "B", "EXEMPT": "E"}
CAT_CODES = {"NONE": "N", "TOOL": "T", "MELEE": "W", "ARMOR": "A", "RANGED": "R", "SHIELD": "S"}

esc = html.escape


# ----------------------------------------------------------------------------------------------- snapshot

def snapshot(mod):
    res = os.path.join(mod, "src", "main", "resources", "data", "cvages")
    os.makedirs(SNAP, exist_ok=True)
    for f in ("age_dump.csv", "gear.json"):
        shutil.copyfile(os.path.join(mod, "tools", f), os.path.join(SNAP, f))

    def load(p):
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)

    data = {"ages": [], "disciplines": {}, "books": [], "quests": [], "auto_quests": {}, "crates": {}, "rewards": {}, "chests": []}
    for p in glob.glob(os.path.join(res, "cvages", "ages", "*.json")):
        a = load(p)
        a["id"] = os.path.basename(p)[:-5]
        data["ages"].append(a)
    data["ages"].sort(key=lambda a: a["order"])
    for p in glob.glob(os.path.join(res, "cvages", "disciplines", "*.json")):
        data["disciplines"][os.path.basename(p)[:-5]] = load(p)
    data["tuning"] = load(os.path.join(res, "cvages", "tuning.json"))
    data["badge_sources"] = load(os.path.join(res, "cvages", "badge_sources.json"))["leaders"]
    for p in sorted(glob.glob(os.path.join(res, "cvages", "books", "*", "*.json"))):
        b = load(p)
        b["id"] = "cvages:" + os.path.relpath(p, os.path.join(res, "cvages", "books")).replace(os.sep, "/")[:-5]
        data["books"].append(b)
    adv = os.path.join(res, "advancement")
    for p in sorted(glob.glob(os.path.join(adv, "**", "*.json"), recursive=True)):
        rel = os.path.relpath(p, adv).replace(os.sep, "/")[:-5]
        a = load(p)
        if rel.startswith("auto/"):
            prev = a["criteria"].get("prev", {}).get("conditions", {}).get("item")
            ings = []
            for k, c in a["criteria"].items():
                if k.startswith("has"):
                    pred = c["conditions"]["items"][0]
                    items = pred["items"] if isinstance(pred["items"], list) else [pred["items"]]
                    ings.append({"items": items, "count": pred.get("count", {}).get("min", 1)})
            data["auto_quests"][rel[5:].replace("/", ":", 1)] = {"prev": prev, "ingredients": ings}
            continue
        d = a.get("display")
        if not d or d.get("hidden"):
            continue
        age = a["criteria"].get("age", a["criteria"].get("reached", {})).get("conditions", {}).get("age")
        data["quests"].append({"id": "cvages:" + rel, "title": d["title"]["text"], "desc": d["description"]["text"],
                               "icon": d["icon"]["id"], "age": age, "frame": d.get("frame", "task"),
                               "kind": rel.split("/")[0], "rewards": a.get("rewards", {})})
    lt = os.path.join(res, "loot_table")
    for p in glob.glob(os.path.join(lt, "prize_crates", "*.json")):
        age = os.path.basename(p)[:-5]
        crate = load(p)
        extras = load(os.path.join(lt, "prize_crates", "extras", age + ".json"))
        data["crates"][age] = {"books": crate["pools"][0]["rolls"], "rolls": crate["pools"][1]["rolls"],
                               "loot": crate["pools"][1]["entries"], "extras": extras["pools"][0]["entries"]}
    maybe = load(os.path.join(lt, "rewards", "maybe_crate_wood.json"))
    data["rewards"]["hidden_chance"] = maybe["pools"][0]["conditions"][0]["chance"]
    java = open(os.path.join(mod, "src", "main", "java", "net", "av1017", "cvages", "content", "LootInjection.java"), encoding="utf-8").read()
    for m in re.finditer(r'put\("([^"]+)", "([^"]+)", ([\d.]+)f\)', java):
        data["chests"].append({"prefix": m.group(1), "age": m.group(2), "chance": float(m.group(3))})
    groups = re.search(r'new String\[\]\{([^}]*)\}', java)
    if groups:
        for g in re.findall(r'"([^"]+)"', groups.group(1)):
            data["chests"].append({"prefix": "rctmod:trainers/groups/" + g, "age": "current", "chance": 1.0})
    with open(os.path.join(SNAP, "cvages.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(f"snapshot: {len(data['books'])} books, {len(data['quests'])} visible quests, {len(data['auto_quests'])} hidden quests")


# ----------------------------------------------------------------------------------------------- data

class Data:
    def __init__(self):
        with open(os.path.join(SNAP, "cvages.json"), encoding="utf-8") as fh:
            d = json.load(fh)
        self.__dict__.update(d)
        with open(os.path.join(SNAP, "age_dump.csv"), encoding="utf-8") as fh:
            self.items = list(csv.DictReader(fh))
        self.by_id = {r["item"]: r for r in self.items}
        self.age_ids = [a["id"] for a in self.ages]
        self.age_names = {a["id"]: a["name"] for a in self.ages}
        self.book_of = {}
        for i, b in enumerate(self.books):
            for it in b["items"]:
                self.book_of[it] = i
        self.quest_items = set(self.auto_quests)
        for q in self.quests:
            if q["kind"] == "mastery":
                self.quest_items.add(q["id"].split("/", 2)[2].replace("/", ":", 1))

    def name(self, item):
        r = self.by_id.get(item)
        if r:
            return r["name"]
        if item.startswith("#"):
            return "any " + item.split(":", 1)[-1].replace("_", " ")
        return item.split(":", 1)[-1].replace("_", " ").title()

    def age_name(self, age):
        return self.age_names.get(age, age.title())

    def select(self, selectors):
        out = []
        for s in selectors:
            if s.startswith("@"):
                out += [r for r in self.items if r["item"].split(":", 1)[0] == s[1:]]
            elif s.startswith("/") and s.endswith("/"):
                rx = re.compile(s[1:-1])
                out += [r for r in self.items if rx.fullmatch(r["item"])]
            elif s in self.by_id:
                out.append(self.by_id[s])
        seen, uniq = set(), []
        for r in out:
            if r["item"] not in seen:
                seen.add(r["item"])
                uniq.append(r)
        return uniq

    def how(self, r):
        """Plain-words 'how do I get to craft/use this' for one dump row."""
        parts = []
        pol, item = r["policy"], r["item"]
        if pol == "BOOK":
            b = self.book_of.get(item)
            parts.append(f'book: <em>{esc(self.books[b]["title"])}</em>' if b is not None else "book-only (no recipe)")
        elif pol == "MUST_LEARN":
            parts.append("must be learned (quest, teacher or practice)")
        elif pol == "EXEMPT":
            parts.append("always free")
        else:
            parts.append("free once its age is reached" if int(r["recipes"] or 0) else "found, not crafted")
        if r["discipline"]:
            parts.append(f"needs {esc(self.disciplines[r['discipline']]['name'])}")
        if r["category"] != "NONE":
            parts.append("gear: skill matters" + ("; mastery quest" if item in self.quest_items else ""))
        return ", ".join(parts)


def mod_of(item):
    return item.split(":", 1)[0]


def mod_name(ns):
    return MOD_NAMES.get(ns, ns)


def age_chip(d, age):
    return f'<span class="cv-age cv-age-{esc(age)}">{esc(d.age_name(age))}</span>'


def table(head, rows, cls="spec"):
    h = "".join(f"<th>{c}</th>" for c in head)
    body = "\n".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="table-scroll"><table class="{cls}">\n<thead><tr>{h}</tr></thead>\n<tbody>\n{body}\n</tbody>\n</table></div>'


def write(name, text):
    os.makedirs(GEN, exist_ok=True)
    with open(os.path.join(GEN, name), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"<!-- generated by tools/pages/gen_cobblevalley.py: don't edit -->\n{text.strip()}\n")


# ----------------------------------------------------------------------------------------------- fragments

def badge_text(a):
    bits = []
    if a["badges"]:
        bits.append(f'{a["badges"]} different gym badge{"s" if a["badges"] > 1 else ""}')
    for q in a["group_quests"]:
        bits.append({"cvages:group/first_steps": "the First Steps quest",
                     "rctmod:trainers/defeat_all_champion": "beat every Champion"}.get(q, q))
    return " + ".join(bits) or "where everyone starts"


def gen_ages(d):
    counts = {a: {"all": 0, "gear": 0, "book": 0, "must": 0} for a in d.age_ids}
    for r in d.items:
        c = counts[r["age"]]
        c["all"] += 1
        c["gear"] += r["category"] != "NONE"
        c["book"] += r["policy"] == "BOOK"
        c["must"] += r["policy"] == "MUST_LEARN"
    rows = []
    for a in d.ages:
        c = counts[a["id"]]
        dims = ", ".join({"minecraft:the_nether": "the Nether", "minecraft:the_end": "the End"}.get(x, x) for x in a["dimensions"])
        rows.append([age_chip(d, a["id"]), esc(badge_text(a)), dims and f"opens {dims}" or "",
                     f'{c["all"]:,}', f'{c["gear"]}', f'{c["book"]}'])
    write("cv-age-table.html", table(["Age", "The group needs", "Opens", "Items", "Gear", "Book-only"], rows))

    mods = {}
    for r in d.items:
        mods.setdefault(mod_of(r["item"]), {a: 0 for a in d.age_ids})[r["age"]] += 1
    rows = []
    for ns, c in sorted(mods.items(), key=lambda kv: -sum(kv[1].values())):
        if ns in ("item", "moonlight", "patchouli"):
            continue
        rows.append([esc(mod_name(ns))] + [str(c[a]) if c[a] else "" for a in d.age_ids])
    write("cv-age-mods.html", table(["Mod"] + [esc(a["name"].replace(" Age", "")) for a in d.ages], rows))


def gen_skill(d):
    t = d.tuning
    rows = []
    for s in (0, 10, 25, 50, 75, 90, 100):
        eff = t["recognizedBase"] + (1 - t["recognizedBase"]) * (s / 100) ** t["curveExponent"]
        rows.append([f"{s}%", f"{round(eff * 100)}%"])
    pre = t["preAgeDiscoveredBase"] + (1 - t["preAgeDiscoveredBase"]) * (t["preAgeSkillCap"] / 100) ** t["curveExponent"]
    write("cv-effect-table.html", table(["Your skill", "Gear works at"], rows) +
          f'<p class="note">Strange Object (not figured out yet): {round(t["preAgeUndiscovered"] * 100)}%. '
          f'Figured out but from a later age: {round(t["preAgeDiscoveredBase"] * 100)}% rising to at most {round(pre * 100)}% '
          f'(skill stops at {t["preAgeSkillCap"]}% until your group reaches its age).</p>')
    q = [("Crude", f'under {t["roughAt"]}%', "55%", "80%"), ("Rough", f'{t["roughAt"]}-{t["fineAt"] - 1}%', "75%", "90%"),
         ("Fine", f'{t["fineAt"]}-99%', "90%", "96%"), ("Masterwork", "100% (mastered)", "100%", "100%")]
    write("cv-quality-table.html", table(["Quality", "Crafter's skill", "Durability", "Strength"], [list(x) for x in q]))
    hold_cap = round(t["discoveryHoldCapFraction"] * t["discoveryThreshold"])
    rows = [["Carry it (hand, off-hand or worn)", f'{t["discoveryHoldPerSecond"]:g} per second', f"gear: only the first {hold_cap} points"],
            ["Mine with it", f'{t["discoveryMine"]:g} per block ({t["discoveryMineCorrect"]:g} if it\'s the right tool)', ""],
            ["Hit something with it", f'{t["discoveryHit"]:g} per hit', ""],
            ["Get hit while wearing it", f'{t["discoveryHurtWearing"]:g} per hit', ""],
            ["Shoot it", f'{t["discoveryShoot"]:g} per shot', ""],
            ["Someone in the group already figured it out", f'x{t["discoveryGroupBonus"]:g}', "applies to everything above"]]
    write("cv-discovery-table.html", f'<p>A Strange Object needs <strong>{t["discoveryThreshold"]:g} points</strong>.</p>' +
          table(["Doing this", "Adds", "Note"], rows))


def gen_quests(d):
    out = []
    for age in d.age_ids:
        qs = [q for q in d.quests if q["age"] == age and q["kind"] in ("mastery", "group")]
        if not qs:
            continue
        rows = []
        for q in sorted(qs, key=lambda q: (q["kind"] != "group", q["title"])):
            desc = q["desc"].replace(" Reward: you master it, plus a Prize Crate.", "").replace(". Reward: you master it, plus a Prize Crate", "")
            rew = "master it + a Prize Crate" if q["kind"] == "mastery" else "the whole group reaches the Stone Age + a Prize Crate"
            rows.append([f'<strong>{esc(q["title"].replace("Master: ", ""))}</strong>', esc(desc), rew])
        out.append(f'<h3>{age_chip(d, age)}</h3>' + table(["Quest", "What you need", "Reward"], rows))
    write("cv-quests.html", "\n".join(out))

    per = {}
    for item, q in d.auto_quests.items():
        r = d.by_id.get(item)
        if not r:
            continue
        per.setdefault(mod_of(item), {a: 0 for a in d.age_ids})[r["age"]] += 1
    rows = [[esc(mod_name(ns)), str(sum(c.values()))] + [str(c[a]) if c[a] else "" for a in d.age_ids if a != "champion"]
            for ns, c in sorted(per.items(), key=lambda kv: -sum(kv[1].values()))]
    write("cv-hidden-count.html", str(len(d.auto_quests)))
    write("cv-hidden-quests.html", table(["Mod", "Quests"] + [esc(a["name"].replace(" Age", "")) for a in d.ages if a["id"] != "champion"], rows))


def gen_disciplines(d):
    rows = []
    gated = {}
    for r in d.items:
        if r["discipline"]:
            gated[r["discipline"]] = gated.get(r["discipline"], 0) + 1
    order = sorted(d.disciplines.items(), key=lambda kv: d.age_ids.index(kv[1]["age"]))
    for did, x in order:
        stations = ", ".join(esc(d.name(b)) for b in x["gated_blocks"] if b in d.by_id) or "(the enchanting table and anvil enchanting)"
        proxies = ", ".join(esc(d.name(p) if not p.startswith("#") else "any armor trim template") for p in x["proxy_items"]
                            if p.startswith("#") or p in d.by_id)
        recipes = f"{gated.get(did, 0)} recipes" if gated.get(did) else ""
        q = next((q for q in d.quests if q["id"].endswith("discipline/" + did)), None)
        rows.append([f'<strong>{esc(x["name"])}</strong>', age_chip(d, x["age"]), stations, recipes, proxies,
                     esc(q["desc"].split(". Reward")[0]) if q else ""])
    write("cv-disciplines.html", table(["Discipline", "Age", "Stations it opens", "Recipes it unlocks", "Teach it by holding", "Quest"], rows))


def entry_text(d, e):
    n = d.name(e["name"])
    cnt = ""
    for f in e.get("functions", []):
        if f["function"] == "minecraft:set_count":
            c = f["count"]
            cnt = f'{c["min"]}-{c["max"]} ' if isinstance(c, dict) else f"{c} "
    return f"{cnt}{esc(n)}"


def gen_crates(d):
    rows = []
    for age in d.age_ids:
        c = d.crates.get(age)
        if not c:
            continue
        books = f'{c["books"]} book{"s" if c["books"] > 1 else ""}'
        loot = ", ".join(entry_text(d, e) for e in c["loot"])
        extras = ", ".join(entry_text(d, e) for e in c["extras"])
        rows.append([age_chip(d, age), books, f'{c["rolls"]} of: {loot}', f"1 of: {extras}"])
    write("cv-crates.html", table(["Crate", "Instruction books", "Supplies", "Pokémon extras"], rows))

    where = {"igloo_chest": "Igloo", "village/": "Village houses", "shipwreck_": "Shipwrecks", "buried_treasure": "Buried treasure",
             "ruined_portal": "Ruined portals", "abandoned_mineshaft": "Mineshafts", "simple_dungeon": "Dungeons",
             "desert_pyramid": "Desert temples", "jungle_temple": "Jungle temples", "pillager_outpost": "Pillager outposts",
             "underwater_ruin_big": "Big ocean ruins", "trial_chambers/reward": "Trial chamber vaults", "woodland_mansion": "Woodland mansions",
             "stronghold_": "Strongholds", "ancient_city": "Ancient cities", "bastion_": "Bastions", "nether_bridge": "Nether fortresses",
             "end_city_treasure": "End cities", "groups/leader": "Kanto/Johto gym leaders", "groups/gym_leader": "Gym leaders",
             "groups/sinnoh_leader": "Sinnoh gym leaders", "groups/elite_four": "The Elite Four", "groups/champion": "Champions"}
    rows = []
    for c in d.chests:
        label = next((v for k, v in where.items() if c["prefix"].endswith(k) or k in c["prefix"]), c["prefix"])
        age = "your group's current age" if c["age"] == "current" else age_chip(d, c["age"])
        rows.append([esc(label), age, "every win" if c["chance"] >= 1 else f'{round(c["chance"] * 100)}% of chests'])
    write("cv-crate-sources.html", table(["Where", "Crate", "How often"], rows))


def gen_books(d):
    out = []
    by_mod = {}
    for b in d.books:
        by_mod.setdefault(b["id"].split(":", 1)[1].split("/")[0], []).append(b)
    for ns in sorted(by_mod, key=lambda n: mod_name(n)):
        rows = []
        for b in sorted(by_mod[ns], key=lambda b: (d.age_ids.index(b["age"]), b["title"])):
            names = sorted({d.name(i) for i in b["items"]})
            shown = ", ".join(esc(n) for n in names[:14]) + (f" and {len(names) - 14} more" if len(names) > 14 else "")
            rows.append([f'<strong>{esc(b["title"].split(": ", 1)[-1])}</strong>', age_chip(d, b["age"]), str(len(b["items"])), shown])
        out.append(f'<h3 id="books-{esc(ns)}">{esc(mod_name(ns))} <span class="note">({len(by_mod[ns])} books)</span></h3>'
                   + table(["Book", "Readable from", "Recipes", "Teaches"], rows))
    write("cv-books.html", "\n".join(out))
    counts = {}
    for b in d.books:
        counts[b["age"]] = counts.get(b["age"], 0) + 1
    write("cv-book-counts.html", '<div class="stats">' + "".join(
        f'<div class="stat"><b>{counts[a]}</b><span>{esc(d.age_name(a))} books</span></div>' for a in d.age_ids if a in counts) + "</div>")


def gen_gear(d):
    gear = [r for r in d.items if r["category"] != "NONE"]
    out = []
    summary = []
    for age in d.age_ids:
        rows_age = [r for r in gear if r["age"] == age]
        if not rows_age:
            continue
        summary.append(f'<a href="#gear-{age}">{esc(d.age_name(age))} ({len(rows_age)})</a>')
        out.append(f'<h3 id="gear-{age}">{age_chip(d, age)} <span class="note">{len(rows_age)} pieces</span></h3>')
        by_mod = {}
        for r in rows_age:
            by_mod.setdefault(mod_of(r["item"]), []).append(r)
        for ns in sorted(by_mod, key=lambda n: (n != "minecraft", mod_name(n))):
            rows = []
            for r in sorted(by_mod[ns], key=lambda r: (r["category"], r["name"])):
                q = d.auto_quests.get(r["item"])
                if q:
                    need = ", ".join(f'{i["count"]} {esc(d.name(i["items"][0]))}' + (" (or similar)" if len(i["items"]) > 1 else "") for i in q["ingredients"])
                    if q["prev"]:
                        need += f'; 60% skill with the {esc(d.name(q["prev"]))}'
                elif r["item"] in d.quest_items:
                    need = "visible quest in the Cobble Valley tab"
                else:
                    need = "practice or a teacher (no recipe to quest for)"
                extra = f' <span class="note">needs {esc(d.disciplines[r["discipline"]]["name"])}</span>' if r["discipline"] else ""
                rows.append([esc(r["name"]) + extra, CATEGORY_NAMES[r["category"]], need])
            out.append(f'<details><summary><strong>{esc(mod_name(ns))}</strong> <span class="note">{len(rows)}</span></summary>'
                       + table(["Piece", "Type", "Mastery quest needs"], rows) + "</details>")
    write("cv-gear.html", '<nav class="jump" aria-label="Jump to age">' + "".join(summary) + "</nav>\n" + "\n".join(out))


def gen_lookup(d):
    mods = {}
    for r in d.items:
        ns, path = r["item"].split(":", 1)
        disc = r["discipline"]
        mods.setdefault(ns, []).append([path, r["name"], d.age_ids.index(r["age"]),
                                        CAT_CODES[r["category"]] + POLICY_CODES[r["policy"]] + ("Q" if r["item"] in d.quest_items else ""),
                                        disc, d.book_of.get(r["item"], -1), int(r["recipes"] or 0)])
    payload = {
        "ages": [a["name"] for a in d.ages],
        "mods": {ns: mod_name(ns) for ns in mods},
        "disciplines": {k: v["name"] for k, v in d.disciplines.items()},
        "books": [b["title"] for b in d.books],
        "items": mods,
    }
    js = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    write("cv-lookup-data.html", f"<script>var CV_DATA = {js};</script>")
    write("cv-lookup-count.html", f"{len(d.items):,}")


# ----------------------------------------------------------------------------------------------- page boxes

DECOR = ["@handcrafted", "@another_furniture", "@mcwfurnitures", "@mcwlights", "@mcwwindows", "@beautify", "@cobblefurnies",
         "@storagedelight", "@botanypots", "@supplementaries"]
PAGES = {
    "roadmap": {"sel": [], "key": ["minecraft:crafting_table", "minecraft:furnace", "minecraft:iron_pickaxe", "minecraft:diamond_pickaxe",
                                   "minecraft:obsidian", "minecraft:enchanting_table", "minecraft:brewing_stand", "minecraft:ender_eye", "minecraft:elytra"], "notes": [
        "The route below still works, but in Cobble Valley it's <strong>paced by ages</strong>: the group reaches the Stone Age with the First Steps quest, "
        "then needs <strong>1 / 3 / 5 / 8 different gym badges</strong> for the Iron, Diamond, Nether and End Ages. "
        'The Nether stays shut until the Nether Age, the End until the End Age (<a href="cv-ages.html">Ages &amp; Badges</a>).',
        "Things from an age you haven't reached are <strong>Strange Objects</strong>: you can pick them up, but they barely work until you figure them out."]},
    "quickstart": {"sel": [], "key": ["minecraft:crafting_table", "minecraft:wooden_pickaxe", "leaf_beds:oak_leaf_bed", "minecraft:torch",
                                      "minecraft:campfire", "minecraft:stone_pickaxe", "minecraft:furnace", "minecraft:iron_pickaxe", "minecraft:shield"], "notes": [
        'Your first night is different: no wool or shears needed. Make a <strong>leaf bed</strong> (3 leaves over 3 sticks), '
        '<strong>torches from leaves on a stick</strong>, and a <strong>campfire</strong> from sticks and logs (<a href="cv-bushcraft.html">Bushcraft</a>).',
        "Wooden tools are free to craft. Anyone holding a crafting table and a wooden pickaxe completes <strong>First Steps</strong>, and the whole group enters the Stone Age.",
        "The furnace, anvil and enchanting table must be <strong>learned</strong> before you can craft them: quest, teacher, or practice."]},
    "join": {"sel": [], "key": [], "notes": [
        "When Cobble Valley launches, the server switches to it. You'll join the same way. On day one: open the quest tab "
        '(the Advancements key, <span class="kbd">L</span>) and find the <strong>Cobble Valley</strong> tab, and read <a href="cv-start.html">Start Here</a>.']},
    "online": {"sel": [], "key": [], "notes": [
        "Right now the server still runs the sandbox world. When Cobble Valley launches it replaces it, with the same address and mod pack "
        '(plus Leaf Beds and Cobble Valley Ages). Your progress there is saved on the server: <a href="cv-start.html">Start Here</a>.']},
    "mods": {"sel": ["@farmersdelight", "@weaversparadise"], "key": ["farmersdelight:cooking_pot", "farmersdelight:skillet",
                                                                      "farmersdelight:cutting_board", "weaversparadise:clothcrafting_station"], "notes": [
        "This page is about <strong>Our World</strong> (26.3). Several of these mods are also in the Cobblemon pack, and in Cobble Valley "
        'Farmer\'s Delight\'s cooking pot, skillet and cutting board need the <strong>Cooking</strong> discipline, and the clothcrafting station needs '
        '<strong>Tailoring</strong> (<a href="cv-disciplines.html">Disciplines</a>).']},
    "cobblemon": {"sel": ["@cobblemon"], "key": ["cobblemon:poke_ball", "cobblemon:great_ball", "cobblemon:ultra_ball", "cobblemon:healing_machine",
                                                 "cobblemon:pc", "cobblemon:pasture", "cobblemon:potion", "cobblemon:exp_candy_s"], "notes": [
        "Catching and healing aren't held back: <strong>Poké Balls, the Healing Machine, the PC, the Pasture, apricorns, berries and potions are Wood Age</strong>.",
        "<strong>Great Balls</strong> and <strong>Ultra Balls</strong> must be learned (quest, teacher, or crafting practice) and belong to the Iron Age.",
        'Prize Crates add Poké Balls, potions and Exp. Candy at every age (<a href="cv-books.html">Books &amp; Prize Crates</a>).']},
    "gyms": {"sel": [], "key": [], "notes": [
        "<strong>Gym badges drive the ages.</strong> Every <em>different</em> gym leader anyone in the group beats is one group badge: "
        "<strong>1</strong> opens the Iron Age, <strong>3</strong> the Diamond Age, <strong>5</strong> the Nether Age, <strong>8</strong> the End Age. "
        "Beating every Champion opens the Champion Age.",
        "Sinnoh leaders count once, whichever of their two fights you win. Badges earned while someone is offline still count when they log in.",
        "Every win against a gym leader, the Elite Four or a Champion also drops a <strong>Prize Crate</strong> for the group's current age."]},
    "twinportals": {"sel": ["@twinportals"], "key": [], "notes": [
        "The Portal Device's age comes from its recipe (see below). Strange Objects can't be used well until you figure them out."]},
    "portalgun": {"sel": ["@ricksportalgun"], "key": [], "notes": ["The portal gun and its parts follow the ages of their ingredients."]},
    "backpack": {"sel": ["@travelersbackpack"], "key": ["travelersbackpack:standard", "travelersbackpack:backpack_tank"], "notes": [
        "Backpacks are crafted normally once their materials' age is reached; the fancy mob and material skins follow their ingredients."]},
    "decorate": {"sel": DECOR, "key": [], "notes": [
        "<strong>Furniture and decorations come from instruction books.</strong> Each book teaches a few pieces (in every wood and color) for good. "
        'Books come from <strong>Prize Crates</strong>: quest rewards, structure chests and gym wins (<a href="cv-books.html">every book</a>).',
        "Tools and workstations from these mods (hammers, the botanist workbench) are ordinary recipes."]},
    "visuals": {"sel": [], "key": [], "notes": ["Nothing changes here: texture packs, shaders and far terrain are the same in Cobble Valley."]},
    "controls": {"sel": [], "key": [], "notes": [
        'Quest book: the Advancements key (<span class="kbd">L</span>), tab <strong>Cobble Valley</strong>.',
        "Teach someone: hold the item you've mastered, <strong>crouch and right-click them</strong>, and stay close until the bar fills.",
        "See where you stand: <code>/ages age</code> (the group's ages and badges) and <code>/ages info</code> (your skills)."]},
    "ships": {"sel": ["@smallships"], "key": [], "notes": ["Ships are crafted once their materials' age is reached; cannons need iron."]},
    "aircraft": {"sel": ["@immersive_aircraft"], "key": [], "notes": ["Aircraft parts follow their materials' ages: engines and hulls need iron."]},
    "wheels": {"sel": ["@pokebike", "@automobility"], "key": [], "notes": ["Bikes and cars follow their ingredients' ages."]},
    "villagers": {"sel": ["@mca"], "key": [], "notes": ["MCA's items follow their ingredients' ages. Trading and families work as usual."]},
    "breeding": {"sel": ["@cobbreeding"], "key": [], "notes": ["Breeding works as usual; Cobbreeding's items follow their ingredients' ages."]},
    "gear": {"sel": ["@magistuarmory", "@immersive_armors", "@cobblemonarmors", "/minecraft:.*_(sword|axe|pickaxe|shovel|hoe|helmet|chestplate|leggings|boots)/",
                     "minecraft:bow", "minecraft:crossbow", "minecraft:shield", "minecraft:trident", "minecraft:mace"],
             "key": ["minecraft:iron_sword", "minecraft:diamond_chestplate", "magistuarmory:steel_ingot", "immersive_armors:heavy_chestplate",
                     "minecraft:netherite_upgrade_smithing_template"], "notes": [
        "<strong>Gear works as well as you know it.</strong> At 0% skill a sword hits at 35% strength and armor protects at 35%; use it and it climbs to 100%. "
        'Crafted gear also has a quality (Crude to Masterwork) set by the crafter\'s skill (<a href="cv-skill.html">Skill &amp; Quality</a>).',
        "Smithing templates and the smithing table need <strong>Blacksmithing</strong>; trainer outfits need <strong>Tailoring</strong>.",
        'Every piece of gear by age, with its mastery quest: <a href="cv-gear.html">Gear by Age</a>.']},
    "mining": {"sel": ["/minecraft:.*_pickaxe/"], "key": [], "notes": [
        "Pickaxes dig at a speed set by your skill with them (35% at 0% skill). A pickaxe that's still a Strange Object to you can't harvest ore at all.",
        "Raw iron, gold, redstone and lapis are Iron Age, and diamonds are Diamond Age: until then they're Strange Objects, and carrying or using them slowly figures them out."]},
    "caving": {"sel": [], "key": ["minecraft:torch", "minecraft:lantern", "minecraft:water_bucket", "minecraft:shield", "minecraft:bow"], "notes": [
        "Early torches come from leaves on a stick, so you can cave before you have coal."]},
    "iron": {"sel": [], "key": ["minecraft:raw_iron", "minecraft:iron_ingot", "minecraft:bucket", "minecraft:iron_pickaxe", "minecraft:iron_chestplate",
                                "minecraft:blast_furnace"], "notes": [
        "Iron is <strong>Iron Age</strong>: the group needs its first gym badge. Before that, iron is a Strange Object: you can mine and store it, "
        "and carrying or smelting it helps you figure it out."]},
    "copper": {"sel": [], "key": ["minecraft:raw_copper", "minecraft:copper_ingot", "minecraft:lightning_rod", "minecraft:spyglass", "minecraft:brush"], "notes": [
        "Copper is a Stone Age metal, so it's the first metal you'll use."]},
    "enchanting": {"sel": [], "key": ["minecraft:enchanting_table", "minecraft:anvil", "minecraft:bookshelf", "minecraft:grindstone"], "notes": [
        "<strong>Enchanting is a discipline</strong> (Diamond Age): learn it from a quest or a master before the enchanting table or anvil will enchant for you.",
        "You can only enchant gear you've <strong>mastered</strong> (100%). Renaming and the grindstone always work.",
        'Enchanted loot shows "enchantments sleep until you master it". In v0.1 that\'s only a warning; v0.2 makes it real.']},
    "farms": {"sel": ["@farmersdelight"], "key": ["farmersdelight:cooking_pot", "farmersdelight:cutting_board", "minecraft:composter", "minecraft:wooden_hoe"],
              "notes": ["Farmer's Delight's cooking pot, skillet and cutting board need the <strong>Cooking</strong> discipline (Stone Age)."]},
    "exploration": {"sel": [], "key": [], "notes": [
        "Structure chests can hold a <strong>Prize Crate</strong> matched to the structure: villages Wood, shipwrecks and mineshafts Stone, "
        "dungeons and temples Iron, strongholds, mansions and ancient cities Diamond, bastions and fortresses Nether, End cities End "
        '(<a href="cv-books.html">full table</a>).',
        "The Nether and the End stay shut until the group reaches their ages."]},
}


def box_html(d, page, spec):
    rows = d.select(spec["sel"])
    parts = ['<aside class="cvx" aria-label="In Cobble Valley">',
             '<div class="cvx-head"><span class="cvx-tag">In Cobble Valley</span>'
             '<a class="cvx-link" href="cv-start.html">What is this?</a></div>']
    if spec["notes"]:
        parts.append("<ul>" + "".join(f"<li>{n}</li>" for n in spec["notes"]) + "</ul>")
    if rows:
        by_age = {}
        for r in rows:
            by_age[r["age"]] = by_age.get(r["age"], 0) + 1
        ages = " · ".join(f'{esc(d.age_name(a).replace(" Age", ""))} {by_age[a]}' for a in d.age_ids if a in by_age)
        book = sum(r["policy"] == "BOOK" for r in rows)
        must = sum(r["policy"] == "MUST_LEARN" for r in rows)
        gear = sum(r["category"] != "NONE" for r in rows)
        disc = {}
        for r in rows:
            if r["discipline"]:
                disc[r["discipline"]] = disc.get(r["discipline"], 0) + 1
        facts = [f"<strong>{len(rows)}</strong> items by age: {ages}"]
        if gear:
            facts.append(f"<strong>{gear}</strong> are gear (skill matters)")
        if book:
            facts.append(f"<strong>{book}</strong> need an instruction book")
        if must:
            facts.append(f"<strong>{must}</strong> must be learned")
        for k, v in disc.items():
            facts.append(f"<strong>{v}</strong> need {esc(d.disciplines[k]['name'])}")
        parts.append('<p class="cvx-facts">' + "; ".join(facts) + ".</p>")
    key = [d.by_id[k] for k in spec["key"] if k in d.by_id]
    if key:
        parts.append('<div class="cvx-scroll"><table class="cvx-table"><thead><tr><th>Item</th><th>Age</th><th>How</th></tr></thead><tbody>'
                     + "".join(f'<tr><td>{esc(r["name"])}</td><td>{esc(d.age_name(r["age"]))}</td><td>{d.how(r)}</td></tr>' for r in key)
                     + "</tbody></table></div>")
    parts.append('<p class="cvx-foot">Any item: <a href="cv-lookup.html">Item Lookup</a>. Outside Cobble Valley (Our World, LAN worlds) none of this applies.</p>')
    parts.append("</aside>")
    return "\n".join(parts)


BOX_CSS = """<style>
.cvx { border: 2px solid var(--accent, #2f7fd8); background: var(--accent-bg, #e2eefb); padding: 12px 16px 10px; margin: 18px 0 8px; font-size: 0.92rem; color: var(--ink-soft, #4a4234); }
.cvx-head { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 6px; align-items: baseline; }
.cvx-tag { font-family: "Silkscreen", monospace; font-size: 0.8rem; color: var(--accent, #2f7fd8); letter-spacing: 0.04em; }
.cvx-link { font-size: 0.8rem; }
.cvx ul { margin: 8px 0 4px; padding-left: 1.2em; }
.cvx li { margin: 3px 0; }
.cvx strong { color: var(--ink, #241f16); }
.cvx-facts { margin: 6px 0; }
.cvx-scroll { overflow-x: auto; }
.cvx-table { width: 100%; border-collapse: collapse; font-size: 0.86rem; margin: 6px 0; }
.cvx-table th { text-align: left; font-family: "Silkscreen", monospace; font-size: 0.66rem; padding: 4px 6px; border-bottom: 2px solid var(--panel-border, #b8ae95); }
.cvx-table td { padding: 5px 6px; border-bottom: 1px solid var(--panel-border, #b8ae95); vertical-align: top; }
.cvx-foot { margin: 6px 0 0; font-size: 0.8rem; color: var(--ink-faint, #7a7161); }
</style>"""


def inject_boxes(d):
    for page, spec in PAGES.items():
        p = os.path.join(DOCS, page + ".html")
        if not os.path.exists(p):
            print("  no page", page)
            continue
        s = open(p, encoding="utf-8").read()
        block = "<!-- cv-box -->\n" + BOX_CSS + "\n" + box_html(d, page, spec) + "\n<!-- /cv-box -->\n"
        write(f"cvbox-{page}.html", block)
        if "<!-- cv-box -->" in s:
            s = re.sub(r"<!-- cv-box -->.*?<!-- /cv-box -->\n?", lambda m: block, s, count=1, flags=re.S)
        else:
            m = re.search(r'\n\s*<nav class="jump"|\n\s*<section', s)
            if not m:
                print("  can't place box on", page)
                continue
            s = s[:m.start()] + "\n" + block + s[m.start():]
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(s)
    print(f"boxes: {len(PAGES)} pages")


def main(argv=None, boxes=True):
    argv = sys.argv[1:] if argv is None else argv
    mod = argv[0] if argv else DEFAULT_MOD
    if os.path.isdir(mod):
        snapshot(mod)
    else:
        print("no mod folder; using the existing snapshot in data/cvages/")
    d = Data()
    gen_ages(d)
    gen_skill(d)
    gen_quests(d)
    gen_disciplines(d)
    gen_crates(d)
    gen_books(d)
    gen_gear(d)
    gen_lookup(d)
    if boxes:
        inject_boxes(d)
    print(f"generated: {len(os.listdir(GEN))} fragments from {len(d.items)} items")


if __name__ == "__main__":
    main()
