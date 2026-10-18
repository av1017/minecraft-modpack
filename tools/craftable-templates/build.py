"""Builds our own data-only Fabric mod with a crafting recipe for every smithing template
(Minecraft 1.21.1). It replaces Craftable Smithing Templates 1.2, whose 1.21 recipe files use
the 1.21.2+ format and fail to load on 1.21.1.

Each recipe is 7 diamonds + a themed item (top middle) + the template's usual copy block
(center), the same layout as vanilla's copy recipe, but without needing a template.

Version 1.1 also adds two recipes from newer Minecraft (26.x) that 1.21.1 lacks: a saddle
(3 leather + 1 iron ingot) and a lead from 5 string with no slime ball.

Usage: python build.py <output dir>   (writes avtemplates-<version>.jar and prints its sha1)
Then upload it as a GitHub release and update the "avtemplates" entry in packs/cobblemon/mods.json.
"""
import hashlib, io, json, os, sys, zipfile

VERSION = "1.1.0"
MOD_ID = "avtemplates"

# template id: (themed item, copy block). "#tag" means an item tag.
RECIPES = {
    "netherite_upgrade_smithing_template": ("netherite_ingot", "netherrack"),
    "sentry_armor_trim_smithing_template": ("iron_ingot", "cobblestone"),
    "vex_armor_trim_smithing_template": ("gold_ingot", "cobblestone"),
    "coast_armor_trim_smithing_template": ("sand", "cobblestone"),
    "wild_armor_trim_smithing_template": ("vine", "mossy_cobblestone"),
    "dune_armor_trim_smithing_template": ("cactus", "sandstone"),
    "tide_armor_trim_smithing_template": ("prismarine_crystals", "prismarine"),
    "ward_armor_trim_smithing_template": ("amethyst_shard", "cobbled_deepslate"),
    "silence_armor_trim_smithing_template": ("sculk", "cobbled_deepslate"),
    "snout_armor_trim_smithing_template": ("porkchop", "blackstone"),
    "rib_armor_trim_smithing_template": ("bone", "netherrack"),
    "eye_armor_trim_smithing_template": ("ender_eye", "end_stone"),
    "spire_armor_trim_smithing_template": ("end_rod", "purpur_block"),
    "wayfinder_armor_trim_smithing_template": ("compass", "terracotta"),
    "raiser_armor_trim_smithing_template": ("dirt", "terracotta"),
    "shaper_armor_trim_smithing_template": ("coarse_dirt", "terracotta"),
    "host_armor_trim_smithing_template": ("#saplings", "terracotta"),
    "flow_armor_trim_smithing_template": ("breeze_rod", "tuff_bricks"),
    "bolt_armor_trim_smithing_template": ("copper_ingot", "copper_block"),
}


def ingredient(name):
    return {"tag": "minecraft:" + name[1:]} if name.startswith("#") else {"item": "minecraft:" + name}


def recipe(template, themed, block):
    # Same shape and JSON layout as vanilla 1.21.1's data/minecraft/recipe/*_smithing_template.json.
    return {
        "type": "minecraft:crafting_shaped",
        "category": "misc",
        "key": {"#": ingredient("diamond"), "C": ingredient(block), "I": ingredient(themed)},
        "pattern": ["#I#", "#C#", "###"],
        "result": {"count": 1, "id": "minecraft:" + template},
    }


# Recipes Minecraft added after 1.21.1 (copied from the 26.3 versions, in 1.21.1's JSON layout).
EXTRA_RECIPES = {
    "saddle": {
        "type": "minecraft:crafting_shaped",
        "category": "equipment",
        "key": {"#": ingredient("iron_ingot"), "X": ingredient("leather")},
        "pattern": [" X ", "X#X"],
        "result": {"count": 1, "id": "minecraft:saddle"},
    },
    "lead_from_string": {
        "type": "minecraft:crafting_shaped",
        "category": "equipment",
        "key": {"~": ingredient("string")},
        "pattern": ["~~ ", "~~ ", "  ~"],
        "result": {"count": 2, "id": "minecraft:lead"},
    },
}


def build(out_dir):
    mod = {
        "schemaVersion": 1,
        "id": MOD_ID,
        "version": VERSION,
        "name": "Craftable Templates & More (our own)",
        "description": "Crafting recipes for every smithing template (7 diamonds, a themed item, and the template's copy block), plus the newer saddle and slime-free lead recipes.",
        "authors": ["Avery Thomas"],
        "contact": {"sources": "https://github.com/av1017/minecraft-modpack/tree/main/tools/craftable-templates"},
        "license": "MIT",
        "environment": "*",
        "depends": {"fabricloader": ">=0.15.0", "minecraft": "~1.21.1", "fabric-resource-loader-v0": "*"},
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("fabric.mod.json", json.dumps(mod, indent=2) + "\n")
        for template, (themed, block) in sorted(RECIPES.items()):
            name = template.replace("_armor_trim_smithing_template", "_trim").replace("_smithing_template", "")
            z.writestr(f"data/{MOD_ID}/recipe/{name}.json", json.dumps(recipe(template, themed, block), indent=2) + "\n")
        for name, data in EXTRA_RECIPES.items():
            z.writestr(f"data/{MOD_ID}/recipe/{name}.json", json.dumps(data, indent=2) + "\n")
    data = buf.getvalue()
    path = os.path.join(out_dir, f"{MOD_ID}-{VERSION}.jar")
    with open(path, "wb") as f:
        f.write(data)
    print(path)
    print("sha1", hashlib.sha1(data).hexdigest())
    print("recipes", len(RECIPES) + len(EXTRA_RECIPES))


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else ".")
