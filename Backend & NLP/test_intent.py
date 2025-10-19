#!/usr/bin/env python3
"""
Test script to debug intent recognition for "who are you" message
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Chatbot.chat import predict_tag, route_message, intents_list

def test_intent_recognition():
    test_message = "who are you"
    print(f"Testing message: '{test_message}'")
    print("=" * 50)
    
    # Test predict_tag function
    tag, confidence = predict_tag(test_message)
    print(f"Predicted tag: '{tag}' (confidence: {confidence})")
    
    # Test route_message function
    response = route_message(test_message)
    print(f"Response: '{response}'")
    
    print("\n" + "=" * 50)
    print("Available intents:")
    for i, intent in enumerate(intents_list):
        intent_name = intent.get("tag", intent.get("intent", "unknown"))
        patterns = intent.get("patterns", intent.get("text", []))
        print(f"{i+1}. {intent_name}: {patterns}")

if __name__ == "__main__":
    test_intent_recognition()
