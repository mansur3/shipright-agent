"""Tiny Excalidraw scene writer used by build_diagrams.py. Emits real Excalidraw elements (rectangles, text, arrows with bindings)
so the files open and stay editable at https://excalidraw.com. Standard library only."""
import json
import random
import textwrap

# Colour convention: blue data/storage, purple AI agents, orange orchestration, green validated, grey external, red risk
CLS = {
    "data": ("#1971c2", "#d0ebff"),
    "agent": ("#6741d9", "#e5dbff"),
    "orch": ("#e8590c", "#ffe8cc"),
    "ok": ("#2f9e44", "#d3f9d8"),
    "ext": ("#868e96", "#f1f3f5"),
    "risk": ("#e03131", "#ffe3e3"),
    "plain": ("#495057", "#ffffff"),
}
INK = "#1e1e1e"
FONT = 2  # Helvetica


class Scene:
    def __init__(self, seed=1):
        self.els = []
        self.rects = {}
        self.rnd = random.Random(seed)
        self.n = 0

    def _base(self, typ, x, y, w, h, **kw):
        self.n += 1
        e = {
            "id": kw.pop("id", f"e{self.n}"), "type": typ, "x": round(x, 1), "y": round(y, 1), "width": round(w, 1), "height": round(h, 1),
            "angle": 0, "strokeColor": INK, "backgroundColor": "transparent", "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
            "roughness": 0, "opacity": 100, "groupIds": [], "frameId": None, "roundness": None, "seed": self.rnd.randint(1, 2**31 - 1),
            "version": 1, "versionNonce": self.rnd.randint(1, 2**31 - 1), "isDeleted": False, "boundElements": [], "updated": 1700000000000,
            "link": None, "locked": False,
        }
        e.update(kw)
        return e

    def text(self, x, y, s, size=16, color=INK, align="left", w=None, bold=False, group=None):
        lines = s.split("\n")
        tw = w or max(len(l) for l in lines) * size * 0.52 + 6
        th = len(lines) * size * 1.25
        e = self._base("text", x, y, tw, th, strokeColor=color, text=s, originalText=s, fontSize=size, fontFamily=FONT, textAlign=align,
                       verticalAlign="top", containerId=None, lineHeight=1.25, autoResize=True, baseline=int(size))
        if group:
            e["groupIds"] = [group]
        self.els.append(e)
        return e

    def box(self, id, x, y, w, h, cls, title, body="", dashed=False, tsize=16, bsize=12, group=None, label=None):
        stroke, fill = CLS[cls]
        g = group or f"g-{id}"
        r = self._base("rectangle", x, y, w, h, id=id, strokeColor=stroke, backgroundColor=fill, roundness={"type": 3}, groupIds=[g],
                       strokeStyle="dashed" if dashed else "solid")
        self.els.append(r)
        self.rects[id] = r
        cy = y + 10
        if label:
            self.text(x + 12, cy, label, 10, stroke, group=g)
            cy += 15
        tl = textwrap.fill(title, width=max(10, int((w - 24) / (tsize * 0.52))))
        t = self.text(x + 12, cy, tl, tsize, INK, group=g, w=w - 24)
        cy += t["height"] + 4
        if body:
            lines = []
            for para in body.split("\n"):
                lines += textwrap.wrap(para, width=max(10, int((w - 24) / (bsize * 0.5)))) or [""]
            self.text(x + 12, cy, "\n".join(lines), bsize, "#343a40", group=g, w=w - 24)
        return r

    def arrow(self, a, b, label=None, pts=None, dashed=False, color="#495057", sa="auto", sb="auto", lsize=11, lx=0, ly=0):
        """Arrow from rect a to rect b (ids). pts overrides the route (absolute points)."""
        ra, rb = self.rects[a], self.rects[b]
        if pts is None:
            ax, ay, bx, by = self._route(ra, rb, sa, sb)
            pts = [(ax, ay), (bx, by)]
        x0, y0 = pts[0]
        rel = [[round(px - x0, 1), round(py - y0, 1)] for px, py in pts]
        xs, ys = [p[0] for p in rel], [p[1] for p in rel]
        e = self._base("arrow", x0, y0, max(xs) - min(xs), max(ys) - min(ys), strokeColor=color, strokeStyle="dashed" if dashed else "solid", roundness=None,
                       points=rel, lastCommittedPoint=None, startArrowhead=None, endArrowhead="arrow", elbowed=False, strokeWidth=2,
                       startBinding={"elementId": a, "focus": 0, "gap": 2}, endBinding={"elementId": b, "focus": 0, "gap": 2})
        self.els.append(e)
        ra["boundElements"].append({"id": e["id"], "type": "arrow"})
        rb["boundElements"].append({"id": e["id"], "type": "arrow"})
        if label:
            mx = sum(p[0] for p in pts) / len(pts) + lx
            my = (pts[0][1] + pts[-1][1]) / 2 + ly if len(pts) == 2 else sum(p[1] for p in pts) / len(pts) + ly
            tw = len(label) * lsize * 0.52 + 8
            self.text(mx - tw / 2, my - lsize * 1.25 - 2, label, lsize, color, align="center", w=tw)
        return e

    def line(self, pts, color="#adb5bd", dashed=True, width=1):
        x0, y0 = pts[0]
        rel = [[round(px - x0, 1), round(py - y0, 1)] for px, py in pts]
        xs, ys = [p[0] for p in rel], [p[1] for p in rel]
        e = self._base("line", x0, y0, max(xs) - min(xs), max(ys) - min(ys), strokeColor=color, strokeWidth=width, strokeStyle="dashed" if dashed else "solid",
                       points=rel, lastCommittedPoint=None, startBinding=None, endBinding=None, startArrowhead=None, endArrowhead=None)
        self.els.append(e)

    def free_arrow(self, pts, label=None, color="#495057", dashed=False, lsize=11, lpos=0.5):
        x0, y0 = pts[0]
        rel = [[round(px - x0, 1), round(py - y0, 1)] for px, py in pts]
        xs, ys = [p[0] for p in rel], [p[1] for p in rel]
        e = self._base("arrow", x0, y0, max(xs) - min(xs), max(ys) - min(ys), strokeColor=color, strokeStyle="dashed" if dashed else "solid",
                       points=rel, lastCommittedPoint=None, startArrowhead=None, endArrowhead="arrow", elbowed=False, startBinding=None, endBinding=None)
        self.els.append(e)
        if label:
            mx = pts[0][0] + (pts[-1][0] - pts[0][0]) * lpos
            my = pts[0][1] + (pts[-1][1] - pts[0][1]) * lpos
            tw = len(label) * lsize * 0.52 + 8
            self.text(mx - tw / 2, my - lsize * 1.25 - 2, label, lsize, color, align="center", w=tw)

    @staticmethod
    def _route(ra, rb, sa, sb):
        acx, acy = ra["x"] + ra["width"] / 2, ra["y"] + ra["height"] / 2
        bcx, bcy = rb["x"] + rb["width"] / 2, rb["y"] + rb["height"] / 2
        dx, dy = bcx - acx, bcy - acy
        if sa == "auto":
            horizontal = abs(dx) * 0.6 >= abs(dy)
            sa = ("right" if dx > 0 else "left") if horizontal else ("bottom" if dy > 0 else "top")
            sb = {"right": "left", "left": "right", "bottom": "top", "top": "bottom"}[sa]
        pt = lambda r, s: {"right": (r["x"] + r["width"], r["y"] + r["height"] / 2), "left": (r["x"], r["y"] + r["height"] / 2),
                           "top": (r["x"] + r["width"] / 2, r["y"]), "bottom": (r["x"] + r["width"] / 2, r["y"] + r["height"])}[s]
        a, b = pt(ra, sa), pt(rb, sb)
        return a[0], a[1], b[0], b[1]

    def title(self, x, y, s, sub=None):
        self.text(x, y, s, 30, INK)
        if sub:
            self.text(x, y + 40, sub, 15, "#495057")

    def legend(self, x, y, items=None):
        items = items or [("data", "Data source / storage"), ("agent", "AI agent / LLM reasoning"), ("orch", "Orchestration / routing"),
                          ("ok", "Validated calculation / business output"), ("ext", "External system"), ("risk", "Error, exception or risk")]
        self.text(x, y, "Legend", 13, "#495057")
        yy = y + 22
        for k, lab in items:
            st, fl = CLS[k]
            self.els.append(self._base("rectangle", x, yy, 22, 14, strokeColor=st, backgroundColor=fl, roundness={"type": 3}, strokeWidth=2))
            self.text(x + 30, yy - 1, lab, 12, "#343a40")
            yy += 20

    def save(self, path):
        doc = {"type": "excalidraw", "version": 2, "source": "https://excalidraw.com", "elements": self.els,
               "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"}, "files": {}}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=1)
