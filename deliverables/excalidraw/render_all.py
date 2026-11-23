"""Re-render every 0*.excalidraw here to exports/*.svg and exports/*.png using gstack's offline Excalidraw bundle
(lib/diagram-render/dist/diagram-render.html). The scene is injected into a copy of the bundle because it is too big for a command line.
Rendering loads the scene with Excalidraw's own library, so a successful render also proves the file imports.
Usage: python render_all.py [work_dir]"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUNDLE = Path.home() / ".claude/skills/gstack/lib/diagram-render/dist/diagram-render.html"
RENDER = Path.home() / ".claude/skills/gstack/bin/gstack-render.ts"
work = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="xrender-"))
work.mkdir(parents=True, exist_ok=True)
(HERE / "exports").mkdir(exist_ok=True)
html = BUNDLE.read_text(encoding="utf-8")
i = html.rfind("</body>")
for f in sorted(HERE.glob("0*.excalidraw")):
    scene = f.read_text(encoding="utf-8")
    page = html[:i] + "<script>window.__SCENE=" + json.dumps(scene) + ";</script>" + html[i:]
    p = work / f"{f.stem}.html"
    p.write_text(page, encoding="utf-8")
    cmd = ["bun", "--no-env-file", "run", str(RENDER), str(p), "--serve-root", str(work), "--wait-selector", "#done",
           "--eval", "window.__excalidrawToSvg(window.__SCENE).then(s => (window.__svg = s))", "--out", str(HERE / "exports" / f"{f.stem}.svg"),
           "--eval", "window.__rasterize(window.__svg, 2400)", "--out", str(HERE / "exports" / f"{f.stem}.png")]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    print(f.name, "->", "OK" if r.returncode == 0 else "FAIL", (r.stdout + r.stderr).strip().splitlines()[-3:] if r.returncode else "")
