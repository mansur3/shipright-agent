# Submission checklist

| # | Deliverable | Status | Where |
|---|---|---|---|
| 1 | Discovery note, 2 pages | Written | `1_Discovery_Note.md` |
| 2 | Architecture note, 2 pages | Written | `2_Architecture_Note.md`; diagrams in `excalidraw/exports/` |
| 3 | Private repo, LangGraph, README, AGENTS.md, tests | In repo, **confirm private on GitHub** | `README.md`, `backend/AGENTS.md` (rules R1 to R7 table, one row per rule), `backend/tests/` (298 pass), `backend/agent/graph.py`, `claims_graph.py` |
| 4 | Deployed pilot, live URL | **To do: add URL here** | Deploy steps in `README.md` (Vercel, root `backend`, region `bom1`, `SANKALP_PUBLIC_DEMO=1`). Test on a device you have not used before |
| 5 | Deck (12 slides max) and demo | Deck exists; **check slide count** | `../Sankalp_Final_Executive_Presentation.pptx`; demo on the live URL |

Before submitting:
- Convert the two notes to PDF and check each is 2 pages (`../../deliverables/build_notes_pdf.py` does this for the older notes).
- `langsmith.txt` holds a LangSmith API key. It is gitignored, but rotate the key if the folder was ever shared.
- Check-set answers are a draft until Neha Bansal signs them; say so in the demo.
