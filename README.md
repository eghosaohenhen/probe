# Probe

A closed-loop PCB debugging agent. Give it your KiCad files (`.kicad_sch` / `.kicad_pcb`) or a schematic image, a photo of the real board and a symptom. With KiCad files it names exact probe points by reference designator, pad and net. It ranks the likely faults, tells you where to probe next and what a healthy reading looks like. Snap a photo of your multimeter, and it reads the value, checks it against the expectation and picks the next probe until it finds the fault.

Built at the Gemini 4 NYC Hackathon (Problem Statement Two: Element 119).

## Model jobs

| Model | Job |
|---|---|
| Gemini Decision 1 | Gates every photo (usable or retake) and judges each measurement against the healthy expectation, with confidence |
| Gemini 4 Hydrogen | Reads the value off the multimeter or scope photo |
| Gemini 4 Carbon | Root-cause reasoning: ranks faults and picks the measurement that best separates them |

## Run

```
pip install -U "google-genai>=3.2.0" flask
export GEMINI_API_KEY=...
python probe.py
```

Open `http://<laptop-ip>:5000` on your phone to use its camera.

## Where it breaks

Tested on a real board: a XIAO ESP32-C3 load-cell board with two NeoPixels (D1, D2). Symptom: one LED works and the other does not. Design given as Eagle/Fusion `.sch` + `.brd` (read as text the same way as KiCad files).

**Decision 1 photo gate (real runs, threshold: `usable` with confidence >= 0.6):**

| Photo | Decision 1 | Result |
|---|---|---|
| Fresh straight-on board photo, handheld, shadow over the bottom half | usable, 0.73 | Passed |
| Screenshot of the same board from a social video: angled, caption text over the board | usable, 0.51 | Rejected, asked for a retake |
| Photo of the layout on a laptop screen, taken at an angle | usable, 0.66 | Passed |

- The gate rejected the compromised photo on low confidence, not by labelling it `retake`. Decision 1's label still said `usable`, so the 0.6 confidence cutoff is what caught it. A photo just over the threshold would get through.
- The angled photo of a laptop screen passed. The gate checks readability, not whether the image is a good source for the design. KiCad/Eagle files are the safer input.

**Not tested yet (being honest):**
- Single-call baseline vs Probe's loop: at the hackathon, `gemini-4-hydrogen` returned 503 "high demand" and `gemini-4-carbon` / `neon` / `argon` did not respond for more than 10 minutes, so neither the baseline nor the reasoning step finished during the event.
- The meter-reading step (Hydrogen read + Decision 1 match/mismatch verdict) was not run on a real meter photo; no meter was on hand.
- No timeout or fallback model when the reasoner is overloaded: the page just hangs. Next step: a short timeout with a "model busy, retry" message, and falling back to another Gemini 4 model.