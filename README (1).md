# Probe

A closed-loop PCB debugging agent. Give it a schematic, a photo of the real board and a symptom. It ranks the likely faults, tells you where to probe next and what a healthy reading looks like. Snap a photo of your multimeter, and it reads the value, checks it against the expectation and picks the next probe until it finds the fault.

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

- TODO: blurry / angled / glare photos
- TODO: baseline (single model call, no measurement loop) vs Probe on the same board
