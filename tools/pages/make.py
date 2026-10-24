"""Rebuilds every generated part of the guide, in order. Run from the modpack folder:
    python -I tools/pages/make.py [path/to/cobble-valley-ages]
1. gen_cobblevalley: snapshot the mod's data and write tools/pages/generated/*.html
2. build: every tools/pages/*.body.html -> docs/<name>.html
3. gen_cobblevalley: the "In Cobble Valley" box on each existing page (after step 2, which rewrites body pages)"""
import glob
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import build  # noqa: E402
import gen_cobblevalley as gen  # noqa: E402

gen.main(sys.argv[1:], boxes=False)
names = sorted(os.path.basename(p)[: -len(".body.html")] for p in glob.glob(os.path.join(here, "*.body.html")))
build.build(gen.DOCS, names)
gen.inject_boxes(gen.Data())
