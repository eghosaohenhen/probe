"""Probe: a closed-loop PCB debugging agent built on Gemini 4.

Model jobs:
  - Gemini Decision 1  -> gates every photo (usable or retake?) and judges each
                          measurement against the healthy expectation.
  - Gemini 4 Hydrogen  -> reads the value off a photo of the multimeter/scope.
  - Gemini 4 Carbon    -> root-cause reasoning: ranks faults, picks the next probe.

Run:
  pip install -U "google-genai>=3.2.0" flask
  export GEMINI_API_KEY=...
  python probe.py        # then open http://<laptop-ip>:5000 on your phone
"""
import html
import json
import os
import re
import uuid

from flask import Flask, request
from google import genai

REASONER = os.environ.get("PROBE_REASONER", "gemini-4-carbon")  # or gemini-4-argon
READER = "gemini-4-hydrogen"
DECIDER = "gemini-decision-1"

client = genai.Client()
beta = genai.Client(http_options={"api_version": "v1beta"})
app = Flask(__name__)
STATE = {"last_id": None, "expected": None, "log": [], "result": None}

SYSTEM = """You are Probe, a hardware debugging agent working with an engineer at the bench.
You get a photo of the real PCB, a symptom, and the design: a schematic image and/or
KiCad source files (.kicad_sch schematic, .kicad_pcb layout).
When KiCad files are present, treat them as ground truth: use their reference designators,
pad numbers, net names and footprint positions, and match them to what you see on the board photo.
Name probe points precisely, e.g. "U1 pad 3 (net +3V3)" to "J1 pad 2 (net GND)".
Reply ONLY with JSON in this shape:
{"faults": [{"fault": "...", "why": "...", "likelihood": 0.0}],
 "next_probe": {"from": "...", "to": "...", "where_on_board": "...", "meter_mode": "..."},
 "expected_healthy": "...",
 "done": false,
 "fix": ""}
List the 3 most likely faults. Pick the ONE measurement that best separates them.
When you receive a measurement, re-rank the faults and pick the next measurement.
Set done=true only when one fault is confirmed, and put the exact rework in "fix"."""

PHOTO_OPTIONS = {
    "usable": "In focus, well lit, and the relevant parts or digits are readable.",
    "retake": "Blurry, glare, cropped, angled, or too far away to read.",
    "other": "Not the kind of image expected.",
}


def log(msg):
    STATE["log"].append(msg)
    print(msg)


def upload(f):
    path = f"/tmp/{uuid.uuid4().hex}_{f.filename}"
    f.save(path)
    return client.files.upload(file=path)


def img(u):
    return {"type": "image", "uri": u.uri, "mime_type": u.mime_type}


def parse(text):
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0))
    except Exception:
        return {"raw": text}


def decide(inputs, question, options):
    d = beta.decisions.create(
        model=DECIDER,
        input=inputs,
        questions={"q": {"type": "choice", "instructions": question, "criteria": options}},
    )
    a = d.answers["q"]
    return a.choice, a.confidence


def gate(u, what):
    choice, conf = decide(
        [img(u), {"type": "text", "text": f"This should be a {what} for PCB debugging."}],
        f"Is this {what} photo usable?",
        PHOTO_OPTIONS,
    )
    log(f"Decision 1 gate on {what}: {choice} (confidence {conf:.2f})")
    return choice == "usable" and conf >= 0.6


def blocks(inputs):
    # Interactions API needs a list of content dicts, not bare strings.
    return [{"type": "text", "text": x} if isinstance(x, str) else x for x in inputs]


def reason(inputs, previous=None):
    r = client.interactions.create(model=REASONER, input=blocks(inputs), previous_interaction_id=previous)
    STATE["last_id"] = r.id
    out = parse(r.output_text)
    STATE["expected"] = out.get("expected_healthy")
    STATE["result"] = out
    log(f"{REASONER}: next probe {out.get('next_probe')}, done={out.get('done')}")


MAX_KICAD_CHARS = 2_000_000  # keep huge layouts from blowing up the request


def kicad_text(field):
    f = request.files.get(field)
    if not f or not f.filename:
        return None
    text = f.read().decode("utf-8", errors="replace")
    if len(text) > MAX_KICAD_CHARS:
        log(f"{f.filename} truncated from {len(text)} to {MAX_KICAD_CHARS} chars")
        text = text[:MAX_KICAD_CHARS]
    log(f"Loaded KiCad file {f.filename} ({len(text)} chars)")
    return f"KiCad file {f.filename}:\n{text}"


@app.post("/start")
def start():
    STATE.update(last_id=None, expected=None, log=[], result=None)
    design = [t for t in (kicad_text("kicad_sch"), kicad_text("kicad_pcb")) if t]
    photos = [(upload(request.files["board"]), "PCB")]
    sch_file = request.files.get("schematic")
    if sch_file and sch_file.filename:
        photos.append((upload(sch_file), "schematic"))
    if not design and len(photos) == 1:
        STATE["result"] = {"raw": "Add a schematic image or KiCad files so Probe knows the design."}
        return page()
    for u, what in photos:
        if not gate(u, what):
            STATE["result"] = {"raw": f"Retake the {what} photo: straight on, in focus, no glare."}
            return page()
    reason([SYSTEM, *[img(u) for u, _ in photos], *design, f"Symptom: {request.form['symptom']}"])
    return page()


@app.post("/measure")
def measure():
    if not STATE["last_id"]:
        return page()
    m = upload(request.files["meter"])
    if not gate(m, "multimeter or oscilloscope screen"):
        STATE["result"] = {**(STATE["result"] or {}), "retake": "Meter photo unreadable. Retake it straight on."}
        return page()
    reading = client.interactions.create(
        model=READER,
        input=blocks([img(m), "Read the value on this meter display with units and mode. Reply with only the reading, e.g. '3.28 V DC'."]),
    ).output_text.strip()
    log(f"{READER} read the meter: {reading}")
    verdict, conf = decide(
        [{"type": "text", "text": f"Expected if healthy: {STATE['expected']}. Measured: {reading}."}],
        "Does the measured value match the healthy expectation?",
        {"match": "Within normal tolerance of the expected value.",
         "mismatch": "Clearly outside the expected value.",
         "other": "Not comparable, e.g. wrong mode or units."},
    )
    log(f"Decision 1 verdict: {verdict} (confidence {conf:.2f})")
    reason([f"Measured {reading}. Decision verdict vs expected: {verdict} ({conf:.2f}). Re-rank and give the next probe."],
           previous=STATE["last_id"])
    return page()


def page():
    e = lambda x: html.escape(str(x))
    r = STATE["result"] or {}
    body = ""
    if "raw" in r:
        body += f"<p><b>{e(r['raw'])}</b></p>"
    if r.get("retake"):
        body += f"<p class=warn>{e(r['retake'])}</p>"
    if r.get("faults"):
        body += "<h3>Likely faults</h3><ol>" + "".join(
            f"<li><b>{e(f.get('fault'))}</b> ({e(f.get('likelihood'))}): {e(f.get('why'))}</li>" for f in r["faults"]) + "</ol>"
    if r.get("done"):
        body += f"<h2>Found it: {e(r.get('fix'))}</h2>"
    elif r.get("next_probe"):
        p = r["next_probe"]
        body += (f"<h3>Next probe</h3><p>{e(p.get('from'))} &rarr; {e(p.get('to'))}<br>"
                 f"Where: {e(p.get('where_on_board'))}<br>Mode: {e(p.get('meter_mode'))}<br>"
                 f"Healthy reading: {e(r.get('expected_healthy'))}</p>")
    trace = "".join(f"<li>{e(x)}</li>" for x in STATE["log"])
    return f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<style>body{{font-family:system-ui;max-width:640px;margin:auto;padding:16px}}.warn{{color:#b00}}
form{{border:1px solid #ccc;border-radius:8px;padding:12px;margin:12px 0}}</style>
<h1>Probe</h1>
<form action=/start method=post enctype=multipart/form-data>
Board photo <input type=file name=board accept="image/*" capture=environment required><br>
KiCad schematic <input type=file name=kicad_sch accept=".kicad_sch,.sch"><br>
KiCad PCB <input type=file name=kicad_pcb accept=".kicad_pcb,.brd"><br>
Schematic image (if no KiCad) <input type=file name=schematic accept="image/*"><br>
Symptom <input name=symptom placeholder="LED never turns on" required>
<button>Start debugging</button></form>
{body}
<form action=/measure method=post enctype=multipart/form-data>
Meter photo <input type=file name=meter accept="image/*" capture=environment required>
<button>Send reading</button></form>
<h3>Agent trace</h3><ol>{trace}</ol>"""


@app.get("/")
def index():
    return page()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)