#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import sys
from typing import Dict, Any

SCRIPT_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))

GLOSS_PATH = os.path.join(ROOT_DIR, 'Glossary', 'arrernte_audio.csv')

try:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'Glossary'))
    from glossary_translator import Glossary as _Glossary, translate as _gloss_translate
except Exception as e:
    print(f"[ERROR] Unable to import glossary translator: {e}")
    sys.exit(1)


def detok(text: str) -> str:
    text = re.sub(r"\s+([.,;:!?])", r"\\1", text)
    return text


def translate_whitelist_en2arr(g: _Glossary, text: str) -> Dict[str, Any]:
    EN_WHITELIST = {
        'headache','fever','cough','stomach','rash','fatigue','pain','temperature','chills','sweating',
        'nausea','vomiting','diarrhea','vision','light','sound','stiff neck','chest','chest pain',
        'shortness of breath','breathless','week','weeks','day','days','hour','hours','front','back','sides','left','right'
    }
    out_text, decisions = _gloss_translate(g, text, direction='en2arr')
    out_tokens = []
    kept = []
    for d in decisions:
        src = (d.get('src_span') or '').strip()
        tgt = (d.get('tgt') or '').strip()
        if src.lower() in EN_WHITELIST and tgt:
            out_tokens.extend(tgt.split(' '))
            kept.append({'src': src, 'tgt': tgt})
        else:
            out_tokens.extend(src.split(' '))
    return { 'text': detok(' '.join(out_tokens)), 'map': kept }


def convert_intents(src_path: str, dst_path: str):
    with open(src_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    intents = data.get('intents')
    if not isinstance(intents, list):
        raise SystemExit("intents.json must contain a top-level 'intents' array")

    g = _Glossary.load_csv(GLOSS_PATH)

    out = { 'intents': [] }
    for intent in intents:
        new_intent = dict(intent)

        # Convert 'text' patterns
        patterns = intent.get('text', intent.get('patterns', []))
        if isinstance(patterns, str):
            patterns = [patterns]
        new_text = []
        for p in patterns or []:
            t = translate_whitelist_en2arr(g, p)
            new_text.append(t['text'])
        new_intent.pop('patterns', None)
        new_intent['text'] = new_text

        # Convert 'responses'
        responses = intent.get('responses', [])
        if isinstance(responses, str):
            responses = [responses]
        new_responses = []
        for r in responses or []:
            t = translate_whitelist_en2arr(g, r)
            new_responses.append(t['text'])
        new_intent['responses'] = new_responses

        out['intents'].append(new_intent)

    with open(dst_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote Arrernte intents to: {dst_path}")


if __name__ == '__main__':
    src = os.path.join(SCRIPT_DIR, 'intents.json')
    dst = os.path.join(SCRIPT_DIR, 'intents_arrernte.json')
    convert_intents(src, dst)



