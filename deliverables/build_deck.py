"""Builds ShipRight_Final_Executive_Presentation.pptx from Project1_Presentation_Template.pptx (its layouts, palette and Arial).
Figures come from deliverables/figures.json (exported from the live Opportunity Register), so the deck matches the app.
Run (needs python-pptx):  python deliverables/build_deck.py <template.pptx>"""
import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Emu, Pt

APP = Path(__file__).resolve().parents[1]
TEMPLATE = Path(sys.argv[1])
F = json.load(open(APP / "deliverables" / "figures.json", encoding="utf-8"))
H, O = F["headline"], F["opps"]
SHOTS, EXP = APP / "deliverables" / "screenshots", APP / "deliverables" / "excalidraw" / "exports"

PURPLE, NAVY, AMBER = RGBColor(0x6D, 0x3F, 0xC9), RGBColor(0x13, 0x1C, 0x3A), RGBColor(0xF0, 0xB4, 0x5C)
CARD, INK, MUTED, LIGHT = RGBColor(0xF5, 0xF5, 0xF8), RGBColor(0x1F, 0x29, 0x33), RGBColor(0x5B, 0x64, 0x74), RGBColor(0xB8, 0xC0, 0xCC)
GREEN, GREENBG = RGBColor(0x2F, 0x9E, 0x44), RGBColor(0xD3, 0xF9, 0xD8)
VIO, VIOBG = RGBColor(0x67, 0x41, 0xD9), RGBColor(0xE5, 0xDB, 0xFF)
RED, REDBG = RGBColor(0xE0, 0x31, 0x31), RGBColor(0xFF, 0xE3, 0xE3)
ORG, ORGBG = RGBColor(0xE8, 0x59, 0x0C), RGBColor(0xFF, 0xE8, 0xCC)
WHITE = RGBColor(255, 255, 255)
IN = 914400
K = 9.0 / 8.2  # content width of the template is 9.0 in; layouts below were laid out on 8.2


def sx(x):
    return 0.5 + (x - 0.5) * K


def inr(v):
    return f"₹{v / 1e7:.2f} cr" if v >= 1e7 else f"₹{v / 1e5:.2f} L"


prs = Presentation(TEMPLATE)
# drop every template slide, keep layouts
lst = prs.slides._sldIdLst
for sid in list(lst):
    prs.part.drop_rel(sid.rId)
    lst.remove(sid)
L = {l.name: l for l in prs.slide_layouts}
for lay in prs.slide_layouts:
    for sh in lay.shapes:
        if sh.has_text_frame and "Your name" in sh.text_frame.text:
            for p_ in sh.text_frame.paragraphs:
                for r_ in p_.runs:
                    r_.text = r_.text.replace("Your name", "ShipRight Agent")


def tb(slide, x, y, w, h, text, size=12, bold=False, color=INK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    s = slide.shapes.add_textbox(Emu(int(sx(x) * IN)), Emu(int(y * IN)), Emu(int(w * K * IN)), Emu(int(h * IN)))
    tf = s.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Emu(36000)
    tf.margin_top = tf.margin_bottom = Emu(18000)
    lines = text if isinstance(text, list) else [text]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = ln
        r.font.size, r.font.bold, r.font.name = Pt(size), bold, "Arial"
        r.font.color.rgb = color
    return s


def card(slide, x, y, w, h, fill=CARD, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    s = slide.shapes.add_shape(shape, Emu(int(sx(x) * IN)), Emu(int(y * IN)), Emu(int(w * K * IN)), Emu(int(h * IN)))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line:
        s.line.color.rgb = line
        s.line.width = Pt(1.25)
    else:
        s.line.fill.background()
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.06
    s.shadow.inherit = False
    return s


def content(title, num):
    s = prs.slides.add_slide(L["CONTENT"])
    ph = next((x for x in s.placeholders if x.placeholder_format.idx == 100), None)
    if ph is None:
        ph = tb(s, 0.5, 0.5, 9.0, 0.6, "", 22, True, INK)
    ph.text = title
    for p in ph.text_frame.paragraphs:
        for r in p.runs:
            r.font.size = Pt(20)
    # section chip, like the template
    c = card(s, 0.5, 0.18, 0.34, 0.26, PURPLE)
    t = tb(s, 0.5, 0.18, 0.34, 0.26, f"{num:02d}", 9, True, WHITE, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
    return s


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def kpi(s, x, y, w, h, label, value, sub, color=INK, bg=CARD):
    card(s, x, y, w, h, bg)
    tb(s, x + 0.1, y + 0.06, w - 0.2, 0.25, label.upper(), 8, True, MUTED)
    tb(s, x + 0.1, y + 0.3, w - 0.2, 0.5, value, 22, True, color)
    tb(s, x + 0.1, y + h - 0.5, w - 0.2, 0.45, sub, 9, False, MUTED)


# ── 1 title
s = prs.slides.add_slide(L["DARK"])
for ph in s.placeholders:
    if ph.placeholder_format.idx == 100:
        ph.text = "ShipRight Agent"
    elif ph.placeholder_format.idx == 101:
        ph.text = "A multi-agent AI financial recovery and channel intelligence solution for the Pfizer channel"
tb(s, 0.6, 1.1, 6, 0.35, "PROJECT 1  ·  THE PFIZER CHANNEL ENGAGEMENT", 13, True, AMBER)
tb(s, 0.6, 4.3, 8, 0.4, "Built and validated on the client's own data pack. Every figure is computed in code; a named person decides every credit.", 11, False, LIGHT)
notes(s, "ShipRight Agent is implemented and running. The app UI is branded Sankalp AI; it is the same solution.")

# ── 2 business challenge
s = content("Money leaks through credits, schemes and stock", 1)
card(s, 0.5, 1.15, 4.0, 3.45, CARD)
tb(s, 0.65, 1.2, 3.7, 0.3, "THE CLIENT'S SITUATION", 9, True, MUTED)
tb(s, 0.65, 1.5, 3.7, 3.0, [
    "Pfizer sells through 6 C&Fs and 156 stockists. 30 months of records, April 2024 to September 2026.",
    "",
    "Claims are credited with no history check: repeats, late filings, packs above supply.",
    "Quarter-end schemes push free goods and returns.",
    "Stock is short at one C&F while another holds months of cover.",
], 12, False, INK)
card(s, 4.7, 1.15, 4.0, 3.45, NAVY)
tb(s, 4.85, 1.2, 3.7, 0.3, "OBJECTIVE", 9, True, AMBER)
tb(s, 4.85, 1.5, 3.7, 0.9, "Recover the most money that the client's own data can legitimately show.", 15, True, WHITE)
tb(s, 4.85, 2.55, 3.7, 2.0, [
    "Find it, size it by formula, show the evidence.",
    "Keep cash, cost, revenue and risk apart.",
    "Never call an opportunity recovered cash.",
    "A named person decides every credit.",
], 12, False, LIGHT)
notes(s, "Source: data-pack CSVs and policy CO-POL-014. The objective is evidence-backed recovery, not volume of findings.")

# ── 3 solution overview
s = content("One checker for claims, schemes and stock", 2)
steps = [("Read", "7 client CSVs cleaned once. Repeats removed, codes normalised, ties to the QBR."),
         ("Check", "Code applies policy to every claim, scheme and stock position. No model decides a rule."),
         ("Size", "Each opportunity gets a formula, evidence and a class. Kinds of money are never added."),
         ("Explain", "Ask Analyst answers in plain words from tool results. A grounding check flags any unsupported figure."),
         ("Decide", "Controller, Supply Chain, CFO or NSM acts. The Review Queue records the decision.")]
for i, (t, b) in enumerate(steps):
    x = 0.5 + i * 1.66
    card(s, x, 1.2, 1.55, 2.05, CARD if i not in (3,) else VIOBG)
    tb(s, x + 0.08, 1.25, 1.4, 0.3, f"{i + 1}  {t}", 12, True, PURPLE)
    tb(s, x + 0.08, 1.6, 1.4, 1.6, b, 10, False, INK)
card(s, 0.5, 3.45, 8.2, 1.15, NAVY)
tb(s, 0.65, 3.5, 8.0, 0.3, "WHAT IS IMPLEMENTED TODAY", 9, True, AMBER)
tb(s, 0.65, 3.78, 7.9, 0.8, "7 agents (5 code-only, 2 with a model), 11 read-only tools, one Opportunity Register, 11 screens on one FastAPI + Next.js app, 298 passing backend tests.", 12, False, WHITE)

# ── 4 multi-agent architecture
s = content("Seven implemented agents: five in code, two with a model", 3)
agents = [("Claim Gatekeeper", "Code", "Checks one claim against window, quantity, repeats, invoice. APPROVE, REJECT or NEEDS A PERSON with clause."),
          ("Claims Mailbox Triage", "Code", "Turns claim emails into structured lines and runs them through the Gatekeeper."),
          ("Recovery Analyst", "Code", "Replays all 4,503 claims and buckets credited, pending and unverifiable money."),
          ("Claims Intake Assistant", "Code + model", "Guides filing a claim; model reads intent and words replies, figures guarded."),
          ("Ask Analyst", "Model + 11 tools", "Picks a read-only tool, explains its result. Max 4 tool trips, 3 guardrail gates."),
          ("Supply and FEFO Watcher", "Code", "Stock cover by C&F, spare stock elsewhere, FEFO breaches, dispatch freeze."),
          ("Scheme Order Gate", "Code", "Free goods against the 3% cap, scheme claim rates, proposed order against stock norm.")]
for i, (n, k, d) in enumerate(agents):
    col, row = i % 2, i // 2
    x, y = 0.5 + col * 4.15, 1.12 + row * 0.86
    llm = "model" in k
    card(s, x, y, 4.05, 0.78, VIOBG if llm else CARD, VIO if llm else None)
    tb(s, x + 0.08, y + 0.03, 2.4, 0.26, n, 11, True, INK)
    tb(s, x + 2.5, y + 0.04, 1.5, 0.24, k.upper(), 8, True, VIO if llm else GREEN, PP_ALIGN.RIGHT)
    tb(s, x + 0.08, y + 0.3, 3.9, 0.46, d, 9, False, MUTED)
card(s, 4.65, 3.7, 4.05, 0.78, GREENBG, GREEN)
tb(s, 4.73, 3.73, 3.9, 0.26, "Opportunity Register (new, not an agent)", 11, True, INK)
tb(s, 4.73, 4.0, 3.9, 0.46, "Lists every money finding with class, formula, evidence, owner and the agent that found it.", 9, False, MUTED)
tb(s, 0.5, 4.55, 8.2, 0.3, "No agent-to-agent LLM handoffs: agents share one validated code layer, so they cannot disagree on a rule. Editable diagrams: deliverables/excalidraw.", 9, False, MUTED)
notes(s, "Source: backend/agent/*.py. Seven agents discovered, seven retained; none removed. See MULTI_AGENT_ARCHITECTURE_AUDIT.md.")

# ── 5 agent collaboration workflow
s = content("Code decides, the model explains, a person acts", 4)
flow = [("Client data", "7 CSVs, read-only", CARD, MUTED), ("Clean + analyse", "clean.py, analysis.py", GREENBG, GREEN), ("Agents", "Gatekeeper, Triage, Recovery, Supply, Scheme", VIOBG, VIO),
        ("Opportunity register", "tiers T1 to T4, classes, formulas", GREENBG, GREEN), ("Validate", "reconcile 23/23, check set 20/20", GREENBG, GREEN),
        ("Explain", "Ask Analyst + grounding check", VIOBG, VIO), ("Act", "named person decides", ORGBG, ORG)]
for i, (t, b, bg, ln) in enumerate(flow):
    x = 0.5 + i * 1.18
    card(s, x, 1.3, 1.08, 1.5, bg, ln)
    tb(s, x + 0.04, 1.35, 1.0, 0.45, t, 10, True, INK, PP_ALIGN.CENTER)
    tb(s, x + 0.04, 1.85, 1.0, 0.9, b, 8, False, MUTED, PP_ALIGN.CENTER)
    if i < 6:
        a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Emu(int(sx(x + 1.08) * IN)), Emu(int(1.95 * IN)), Emu(int(0.1 * IN)), Emu(int(0.2 * IN)))
        a.fill.solid(); a.fill.fore_color.rgb = MUTED; a.line.fill.background()
card(s, 0.5, 3.0, 4.0, 1.55, CARD)
tb(s, 0.6, 3.04, 3.8, 0.28, "WHERE VALIDATION HAPPENS", 9, True, MUTED)
tb(s, 0.6, 3.32, 3.8, 1.2, ["Input guard before the model sees a question", "Tool guard: allow-list, args, 4-trip cap", "Output guard: scrub + numeric grounding check", "Every claim verdict carries rule, clause, file lines"], 10, False, INK)
card(s, 4.7, 3.0, 4.0, 1.55, CARD)
tb(s, 4.8, 3.04, 3.8, 0.28, "EXECUTION AS IMPLEMENTED", 9, True, MUTED)
tb(s, 4.8, 3.32, 3.8, 1.2, ["Strictly sequential; no parallel agents", "Code-only claim check: 0 model calls", "Human approval at the Review Queue only", "Green = code, purple = model, orange = person"], 10, False, INK)
notes(s, "Diagrams 03 and 05 in deliverables/excalidraw show this in full (see appendix slides).")

# ── 6 key business findings
s = content("Most claims are valid; the money sits in a few places", 5)
find = [(inr(H["credited_cash_to_review_inr"]), "credited against policy rules", "478 of 4,112 credited claims; about " + inr(F["per_year"]) + " a year"),
        (inr(H["cash_to_hold_inr"]), "pending claims fail a rule today", f"{O['OPP-03']['claims']} claims: hold before credit"),
        (inr(O["OPP-05"]["amount_inr"]), "expiry returns above the 1% target", f"last 4 quarters; scheme packs claimed at {F['scheme']['scheme_pack_rate_pct']}% vs {F['scheme']['other_pack_rate_pct']}%"),
        (inr(O["OPP-04"]["amount_inr"]), "free goods above the 3% cap", "last 4 quarters; cap exceeded in 7 of 10 quarters"),
        (inr(O["OPP-06"]["amount_inr"]), "revenue a reallocation could serve", f"latest month-end, at PTS. Lucknow: {F['lucknow']['share_of_stock_pct']}% of stock, {F['lucknow']['share_of_outward_pct']}% of outward"),
        ("59%", "of Kolkata lines break FEFO", "last two quarters; 0% at the other five C&Fs")]
for i, (v, t, sub) in enumerate(find):
    col, row = i % 3, i // 3
    x, y = 0.5 + col * 2.76, 1.15 + row * 1.7
    card(s, x, y, 2.66, 1.6, CARD)
    tb(s, x + 0.1, y + 0.08, 2.46, 0.5, v, 22, True, PURPLE)
    tb(s, x + 0.1, y + 0.62, 2.46, 0.4, t, 11, True, INK)
    tb(s, x + 0.1, y + 1.02, 2.46, 0.55, sub, 9, False, MUTED)
tb(s, 0.5, 4.55, 8.2, 0.3, "Different kinds of money: credited cash, cost, revenue at PTS. They are never added. Source: Recovery Register, reconciled to the source CSVs.", 9, False, MUTED)
notes(s, "All figures live from /api/analytics/opportunities. Kolkata FEFO: 1,713 of 2,898 lines in the last two quarters.")

# ── 7 financial recovery opportunities
s = content("Recovery opportunities: confirmed, potential, not cash", 6)
cd = CategoryChartData()
cd.categories = ["Confirmed (T1)", "Potential (T2)", "Hold (pending)"]
cd.add_series("INR lakh", (round(H["confirmed_leakage_inr"] / 1e5, 2), round(H["potentially_recoverable_inr"] / 1e5, 2), round(H["cash_to_hold_inr"] / 1e5, 2)))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Emu(int(0.5 * IN)), Emu(int(1.15 * IN)), Emu(int(3.6 * K * IN)), Emu(int(3.2 * IN)), cd)
ch = gf.chart
ch.has_legend = False
ch.has_title = True
ch.chart_title.text_frame.text = "Cash, ₹ lakh (not added together)"
ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(10)
pl = ch.plots[0]
pl.has_data_labels = True
pl.data_labels.font.size = Pt(10)
pl.data_labels.number_format = '0.00'
pl.data_labels.number_format_is_linked = False
pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
pl.gap_width = 60
for i, c in enumerate((RED, ORG, GREEN)):
    pt = pl.series[0].points[i]
    pt.format.fill.solid()
    pt.format.fill.fore_color.rgb = c
ch.category_axis.tick_labels.font.size = Pt(9)
ch.value_axis.tick_labels.font.size = Pt(9)
ch.value_axis.has_major_gridlines = False
rows = [("CONFIRMED LEAKAGE", f"{inr(H['confirmed_leakage_inr'])}  ·  {O['OPP-01']['claims']} claims", "Policy text breached. Set-off needs Controller.", RED, REDBG),
        ("POTENTIALLY RECOVERABLE", f"{inr(H['potentially_recoverable_inr'])}  ·  {O['OPP-02']['claims']} claims", "Probable breach. Owner confirms each.", ORG, ORGBG),
        ("COST AVOIDANCE", f"{inr(H['cash_to_hold_inr'])}  ·  {O['OPP-03']['claims']} pending", "Not paid yet. Hold.", GREEN, GREENBG),
        ("COST SAVING, NOT CASH", f"{inr(O['OPP-05']['amount_inr'])} returns + {inr(O['OPP-04']['amount_inr'])} free goods", "Scheme design. Overlapping, not additive.", VIO, VIOBG),
        ("REVENUE OPPORTUNITY", f"{inr(O['OPP-06']['amount_inr'])} at PTS", "Not cash, not margin. Allocation inferred.", RGBColor(0x19, 0x71, 0xC2), RGBColor(0xD0, 0xEB, 0xFF))]
for i, (lab, val, sub, c, bg) in enumerate(rows):
    y = 1.12 + i * 0.7
    card(s, 4.3, y, 4.4, 0.64, bg, c)
    tb(s, 4.38, y + 0.02, 2.2, 0.2, lab, 8, True, c)
    tb(s, 4.38, y + 0.2, 4.25, 0.25, val, 11, True, INK)
    tb(s, 4.38, y + 0.42, 4.25, 0.2, sub, 8, False, MUTED)
tb(s, 0.5, 4.5, 8.2, 0.35, "Not quantified (no evidence of loss): ₹1.44 cr claims needing a person, ₹85.45 L unverifiable, Kolkata FEFO, short-dated dispatch. Owners and priority per item are in the Recovery Register.", 9, False, MUTED)
notes(s, "Revenue opportunity is the allocation-fixable shortfall at the latest month-end only. The six-month sum (₹10.18 cr) counts a persistent gap once per month and is not used.")

# ── 8 application demonstration
s = content("Where we lose money, how much, and the proof", 7)
for i, (fn, cap) in enumerate((("01_recovery_dashboard.png", "Recovery: headline, evidence tiers, top stockists"), ("02_recovery_register.png", "Recovery Register: formula, evidence, owner, agent, validation"))):
    x = 0.5 + i * 4.15
    pic = s.shapes.add_picture(str(SHOTS / fn), Emu(int(sx(x) * IN)), Emu(int(1.12 * IN)), width=Emu(int(4.05 * K * IN)))
    pic.crop_bottom = 0.0
    if pic.height > Emu(int(2.75 * IN)):  # crop to a fixed window so both line up
        keep = (2.75 * IN) / pic.height  # picture window height
        pic.crop_bottom = 1 - keep
        pic.height = Emu(int(2.75 * IN))
    pic.line.color.rgb = LIGHT
    tb(s, x, 3.9, 4.05, 0.25, cap, 9, True, INK)
tb(s, 0.5, 4.2, 8.2, 0.6, ["Also live: Check a Claim (0 model calls), Scheme Returns, Allocation, FEFO and Cap, Ask AI with grounding warning, Review Queue, Agents (roles and workflows).",
                          "Removed: the Stockists page, which showed whole-claim 'zero invoice' and 'duplicate' totals the ledger shows are overstated."], 9, False, MUTED)
notes(s, "Screenshots taken from the running app in CFO demo role: deliverables/screenshots.")

# ── 9 technical validation and impact
s = content("Validated against the source data", 8)
kp = [("298", "backend tests pass", "0 failed; 17 added in this audit"), ("20 / 20", "check-set records right", "claim answers agreed by hand"),
      ("23 / 23", "independent reconciliations", "stdlib recompute from the CSVs"), ("0", "type or lint errors", "tsc and next lint; build exports 13 routes")]
for i, (v, t, sub) in enumerate(kp):
    kpi(s, 0.5 + i * 2.07, 1.12, 1.98, 1.15, t, v, sub, PURPLE)
card(s, 0.5, 2.45, 4.0, 2.1, CARD)
tb(s, 0.6, 2.48, 3.8, 0.25, "CORRECTIONS MADE", 9, True, MUTED)
tb(s, 0.6, 2.76, 3.8, 1.8, ["Shortage headline ₹10.18 cr counted one gap once per month; the opportunity now uses the latest month-end (₹2.88 cr, ₹1.04 cr fixable)",
                            "Ask answers now flag any figure no tool returned",
                            "Reply-wording guard rejects new figures",
                            "Hardcoded dashboard KPI replaced by a computed value"], 9, False, INK)
card(s, 4.7, 2.45, 4.0, 2.1, CARD)
tb(s, 4.8, 2.48, 3.8, 0.25, "NOT VERIFIED, SAID PLAINLY", 9, True, MUTED)
tb(s, 4.8, 2.76, 3.8, 1.8, ["Live model answers were not re-run against a paid API in this audit; the guards are unit-tested",
                            "Allocation basis is inferred (share table not in the pack)",
                            "Returns estimate rests on the CFO's 1% target (ledger range ₹2.7 to 3.4 cr; computed ₹3.45 cr)",
                            "No browser end-to-end suite exists; pages were checked by hand"], 9, False, INK)
notes(s, "See QA_AND_VALIDATION_REPORT.md and AI_AGENT_EVALUATION_REPORT.md.")

# ── 10 recommendations
s = content("Next steps for management, and what we still need", 9)
acts = [("Controller", "Raise set-off on the 104 T1 claims; confirm the 374 T2; hold the 69 pending."),
        ("CFO and NSM", "Approve the next scheme circular only inside the 3% cap; gate quarter-end orders with the Scheme Order Gate."),
        ("Supply Chain", "Move spare stock to Lucknow before the monthly allocation; raise Kolkata FEFO with the C&F."),
        ("Demand Planning", "Confirm the outward definition so the allocation basis stops being an inference.")]
for i, (who, what) in enumerate(acts):
    y = 1.12 + i * 0.72
    card(s, 0.5, y, 4.7, 0.66, CARD)
    tb(s, 0.58, y + 0.03, 1.4, 0.6, who, 10, True, PURPLE, anchor=MSO_ANCHOR.MIDDLE)
    tb(s, 1.95, y + 0.03, 3.2, 0.62, what, 9, False, INK, anchor=MSO_ANCHOR.MIDDLE)
card(s, 5.4, 1.12, 3.3, 2.82, NAVY)
tb(s, 5.5, 1.16, 3.1, 0.25, "NEEDED FROM THE CLIENT", 9, True, AMBER)
tb(s, 5.5, 1.45, 3.1, 2.5, ["Archive batch master for 971 claims (₹85.45 L)", "Scheme exceptions approved by the CFO", "Allocation share table", "GST rate and option for late credit notes (exposure only)", "Order padding view to size lost sales"], 10, False, WHITE)
tb(s, 0.5, 4.1, 8.2, 0.6, "Next 30 days: run set-off on T1, switch the claim checker on as a gate before every credit note, review the register monthly with the same reconciliation.", 11, True, INK)

# ── appendix: diagrams
for n, (fn, title) in enumerate((("01_system_architecture.png", "Appendix A. System architecture (Excalidraw export)"),
                                 ("05_agent_execution_sequence.png", "Appendix B. Agent execution sequence (Excalidraw export)"),
                                 ("04_financial_recovery_workflow.png", "Appendix C. Financial recovery workflow (Excalidraw export)"))):
    s = content(title, 10 + n)
    from PIL import Image
    w, h = Image.open(EXP / fn).size
    maxw, maxh = 9.0, 3.65
    sc = min(maxw / w, maxh / h)
    pw, ph = w * sc, h * sc
    s.shapes.add_picture(str(EXP / fn), Emu(int((0.5 + (9.0 - pw) / 2) * IN)), Emu(int(1.12 * IN)), Emu(int(pw * IN)), Emu(int(ph * IN)))
    tb(s, 0.5, 4.8, 8.2, 0.25, "Editable source in deliverables/excalidraw. Also available: 02 multi-agent collaboration, 03 end-to-end workflow.", 8, False, MUTED)

# ── closing
s = prs.slides.add_slide(L["DARK"])
for ph in s.placeholders:
    if ph.placeholder_format.idx == 100:
        ph.text = f"{inr(H['credited_cash_to_review_inr'])} to review, {inr(H['cash_to_hold_inr'])} to hold, one rule set"
    elif ph.placeholder_format.idx == 101:
        ph.text = "Thank you. Questions?"
out = APP / "ShipRight_Final_Executive_Presentation.pptx"
prs.save(out)
print("saved", out, len(prs.slides), "slides")
