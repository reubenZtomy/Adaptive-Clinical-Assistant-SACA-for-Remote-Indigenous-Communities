from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
import re

# ----------------------------
# Basic vocab (extendable)
# ----------------------------
DEFAULT_SYMPTOMS = [
    "fever", "pain", "headache", "cough", "vomiting", "diarrhea",
    "shortness of breath", "chest pain", "stomach ache", "sore throat",
    "dizziness", "nausea"
]

AGE_PAT = re.compile(r"\b(\d{1,3})\s*(?:years?|yrs?|y/o|yo)\b", re.IGNORECASE)
# also match "I am 23", "I'm 45"
AGE_FREE_PAT = re.compile(r"\b(?:i\s*am|i'?m)\s*(\d{1,3})\b", re.IGNORECASE)

def load_symptoms_from_file(path: str | None) -> List[str]:
    if not path:
        return DEFAULT_SYMPTOMS
    try:
        with open(path, "r", encoding="utf-8") as f:
            vals = [ln.strip().lower() for ln in f if ln.strip()]
            return vals or DEFAULT_SYMPTOMS
    except Exception:
        return DEFAULT_SYMPTOMS

SYMPTOMS = set(load_symptoms_from_file("data/nlu/symptoms_en.txt"))

# ----------------------------
# Simple entity detectors
# ----------------------------
def detect_symptoms(text: str) -> List[Dict]:
    found = []
    low = text.lower()
    for s in sorted(SYMPTOMS, key=len, reverse=True):
        if s in low:
            # naive span detection (first occurrence)
            start = low.find(s)
            found.append({
                "label": "SYMPTOM",
                "text": text[start:start+len(s)],
                "start": start,
                "end": start+len(s)
            })
    return found

def detect_age(text: str) -> List[Dict]:
    ents = []
    for m in AGE_PAT.finditer(text):
        age = int(m.group(1))
        ents.append({"label": "AGE", "text": m.group(0), "value": age, "start": m.start(), "end": m.end()})
    for m in AGE_FREE_PAT.finditer(text):
        age = int(m.group(1))
        ents.append({"label": "AGE", "text": m.group(0), "value": age, "start": m.start(), "end": m.end()})
    return ents

def detect_location(text: str) -> List[Dict]:
    # extremely naive: capture a single capitalized word after "in "
    m = re.search(r"\bin\s+([A-Z][a-zA-Z\-]+)\b", text)
    if not m:
        return []
    return [{"label": "LOCATION", "text": m.group(1), "start": m.start(1), "end": m.end(1)}]

# ----------------------------
# Multi-intent rules & scoring
# ----------------------------
@dataclass
class IntentRule:
    name: str
    patterns: list[str]     # regex patterns (case-insensitive)
    base_weight: float      # base score if any pattern matches
    per_match: float        # add per matched pattern
    hard: bool = False      # if True, can hard-override others (e.g., emergency)

# Priority for choosing a primary when multiple match
INTENT_PRIORITY = {
    "emergency": 3,
    "find_clinic": 2,
    "symptom_check": 1,
    "greeting": 0,
}

# Define keyword/regex cues per intent
INTENT_RULES: list[IntentRule] = [
    IntentRule(
        "emergency",
        patterns=[
            r"\bnot breathing\b",
            r"\bunconscious\b",
            r"\b(severe|bad|worse)\s+(bleeding|pain)\b",
            r"\bbleeding (badly|a lot)\b",
            r"\bchest pain\b",
            r"\bheart attack\b",
            r"\bemergency\b",
            r"\bcall (?:000|112|911)\b",
        ],
        base_weight=3.0,
        per_match=1.5,
        hard=True,
    ),
    IntentRule(
        "find_clinic",
        patterns=[
            r"\bnearest (?:clinic|hospital|doctor)\b",
            r"\b(where|how) (?:can|do) i (?:go|find)\b",
            r"\bsee (?:a )?doctor\b",
            r"\bopen (?:now|today)\b",
            r"\bclinic\b",
            r"\bhospital\b",
            r"\bdoctor\b",
        ],
        base_weight=1.5,
        per_match=0.6,
    ),
    IntentRule(
        "symptom_check",
        patterns=[
            r"\bi (?:have|feel|got)\b",
            r"\bsymptom[s]?\b",
            r"\bpain\b",
            r"\bfever\b",
            r"\bcough\b",
            r"\bheadache\b",
            r"\bshortness of breath\b",
            r"\bnausea|vomiting|diarrhea|dizzy|dizziness\b",
        ],
        base_weight=1.0,
        per_match=0.5,
    ),
    IntentRule(
        "greeting",
        patterns=[
            r"^(?:hi|hello|hey|good (?:morning|afternoon|evening)|palya)\b",
            r"\bpalya\b",
            r"\bhello\b",
            r"\bhi\b",
        ],
        base_weight=0.4,
        per_match=0.2,
    ),
]

# Precompile regex
_COMPILED = [(r.name, [re.compile(p, re.IGNORECASE) for p in r.patterns], r) for r in INTENT_RULES]

def _score_patterns(text: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    for name, regs, rule in _COMPILED:
        matches = sum(1 for rgx in regs if rgx.search(text))
        if matches:
            scores[name] = rule.base_weight + rule.per_match * matches
    return scores

def classify_intents(text: str, entities: list[dict] | None = None) -> dict:
    """
    Multi-intent classifier with priorities.
    Returns:
      {
        'primary': str,                 # chosen main intent
        'intents': [{'name', 'score'}], # all matched intents with scores, sorted by priority then score
        'tags': [str]                   # auxiliary tags like greeting
      }
    """
    low = text.lower()
    scores = _score_patterns(low)

    # Entity-aware boosts
    entities = entities or []
    if any(e.get("label") == "SYMPTOM" for e in entities):
        scores["symptom_check"] = scores.get("symptom_check", 0.0) + 0.8

    # Keep greeting as a tag if present
    tags = []
    if "greeting" in scores:
        tags.append("greeting")

    # Hard override if emergency present
    if "emergency" in scores:
        primary = "emergency"
    else:
        # choose best non-greeting by (priority, score)
        candidates = [(n, s) for n, s in scores.items() if n != "greeting"]
        if candidates:
            def sort_key(item):
                n, s = item
                return (INTENT_PRIORITY.get(n, 0), s)
            primary = max(candidates, key=sort_key)[0]
        else:
            primary = "greeting" if "greeting" in scores else "unknown"

    intents_sorted = sorted(
        [{"name": n, "score": round(s, 3)} for n, s in scores.items()],
        key=lambda x: (INTENT_PRIORITY.get(x["name"], 0), x["score"]),
        reverse=True
    )
    return {"primary": primary, "intents": intents_sorted, "tags": tags}

# ----------------------------
# Public API
# ----------------------------
def analyze(text: str) -> Dict:
    """
    Return a structured NLU result:
      {
        'intent':        <primary intent>,
        'intents':       [ {name, score}, ... ],
        'tags':          [ 'greeting', ... ],
        'entities':      [ ... ]
      }
    """
    ents: List[Dict] = []
    ents += detect_symptoms(text)
    ents += detect_age(text)
    ents += detect_location(text)

    intent_info = classify_intents(text, ents)
    return {
        "intent": intent_info["primary"],
        "intents": intent_info["intents"],
        "tags": intent_info["tags"],
        "entities": ents
    }
