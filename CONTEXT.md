# Handoff context for Probe (Gemini 4 NYC Hackathon)

Read this first. It's everything a new coding session needs to keep building.

## Situation (as of 3:25 PM, Sat Nov 21 2026)

- Event: Gemini 4 NYC Hackathon (Cerebral Valley x Google DeepMind), The Malin, 220 W 26th St.
- **Submissions are due at 5:00 PM.** The builder (Eghosa) arrived at 2:30 and is solo.
- `probe.py` has been written but **NOT run yet**. The SDK calls follow the event's Builder Guide examples, but the exact shapes (file upload dicts, `decisions.create`, `interactions.create` with `previous_interaction_id`) need to be checked against the live API. Fix errors first.

## Project: Probe

A closed-loop PCB debugging agent. Input: KiCad source (`.kicad_sch` and/or `.kicad_pcb`, read as text and passed to the reasoner as ground truth for ref designators, pads and nets) or a schematic image, plus a photo of the real board and a symptom. KiCad files are capped at 2M chars each in `kicad_text()`. Output: ranked likely faults, the next probe point with the expected healthy reading. The user photographs their multimeter, and the loop repeats until one fault is confirmed and a rework is named.

Pitch hook: Eghosa's Instagram reel debugging a PCB got 180k views and 100+ comments from people relating and trying to help debug.

## Model jobs (rule: at least 2 Gemini 4 models, each with a clear job)

- **Gemini Decision 1** (`gemini-decision-1`, v1beta client): gates every photo (usable/retake) and judges measured vs expected (match/mismatch/other) with confidence.
- **Gemini 4 Hydrogen** (`gemini-4-hydrogen`): reads the value off the meter photo.
- **Gemini 4 Carbon** (`gemini-4-carbon`, or `gemini-4-argon` via `PROBE_REASONER`): root-cause reasoning, fault ranking, next probe.

## Hard rules from the participant guide

- Problem Statement Two ("Element 119"): images/video/audio must be the core input. Show where it breaks.
- **Banned:** Streamlit apps, plain "image analyzers", dashboards as the main feature. Frame Probe as an agent that runs a measure-and-decide loop, not a photo analyzer. The UI is Flask + plain HTML on purpose.
- Repo must be **public**. Demo must only show work built during the hackathon.
- Submission: 1-minute demo video at https://cerebralvalley.ai/e/gemini-4-nyc/hackathon/submit
- Don't pass temperature/top-p/top-k or legacy thinking-budget fields to Gemini 4 models. Don't pass `minimal` thinking level to Neon/Hydrogen. Don't ship exposed API keys.

## Judging (Round One: 3 min live demo + 2 min Q&A)

- Live Demo 35%: works live on real, unrehearsed inputs.
- Proof It Works 25%: baseline comparison, honest failure cases.
- Creativity 20%: beyond a text interface in a way that matters.
- Gemini 4 & Decisions API Use 20%: at least two models with clear jobs, plus the Decisions API.

## Remaining plan

1. Get `python probe.py` running (`pip install -U "google-genai>=3.2.0" flask`, `GEMINI_API_KEY` from the hackathon account handed out at check-in).
2. One full loop on a real board by ~4:00.
3. Proof by ~4:25: single-call baseline ("what's wrong with this board?") vs Probe's loop on the same board; blurry/angled/glare photos caught by the Decision 1 gate. Fill in "Where it breaks" in README.md.
4. Push, record a 1-minute video by ~4:45, submit by 5:00.

Cut if short on time: live video, reading the meter straight from a camera stream, firmware generation, Managed Agents. Mention them as next steps in the pitch.