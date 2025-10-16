# Educational example – NOT for clinical use.
# Trains a simple classifier from an Excel file and predicts from user-entered symptoms.

import argparse
import joblib
import os
import sys
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix

SYMPTOMS = [
    "fever", "cough", "fatigue", "headache", "nausea",
    "shortness_of_breath", "sore_throat"
]
MODEL_PATH = "medical_model.joblib"
LABELS_PATH = "label_list.npy"

def load_dataset(xlsx_path: str):
    df = pd.read_excel(xlsx_path)
    missing = {"disease"} - set(df.columns)
    missing |= set(SYMPTOMS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    X = df[SYMPTOMS].astype(int).clip(0, 3).values
    y_str = df["disease"].astype(str).values
    # Map string labels to indices
    labels, y = np.unique(y_str, return_inverse=True)
    return X, y, labels

def build_pipeline():
    # Simple, strong baseline: Standardize then Logistic Regression
    # class_weight='balanced' helps when classes are imbalanced
    return Pipeline([
        ("scaler", StandardScaler(with_mean=True, with_std=True)),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", multi_class="auto"))
    ])

def train(xlsx_path: str, test_size=0.2, random_state=42):
    X, y, labels = load_dataset(xlsx_path)
    if len(np.unique(y)) < 2:
        raise ValueError("Need at least two disease classes to train.")

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    pipe = build_pipeline()
    pipe.fit(X_tr, y_tr)

    # Evaluate
    y_pred = pipe.predict(X_te)
    print("=== Evaluation on Hold-out Set ===")
    print(classification_report(y_te, y_pred, target_names=labels))
    print("Confusion matrix (rows=true, cols=pred):")
    print(confusion_matrix(y_te, y_pred))

    # Persist model + labels
    joblib.dump(pipe, MODEL_PATH)
    np.save(LABELS_PATH, labels)
    print(f"\nSaved model to {MODEL_PATH} and labels to {LABELS_PATH}")

def ask_user_symptoms():
    print("\nEnter symptom severities 0–3 (0=absent, 1=mild, 2=moderate, 3=severe).")
    vals = []
    for s in SYMPTOMS:
        while True:
            try:
                v = input(f"{s.replace('_',' ').title()}: ").strip()
                if v.lower() in {"q", "quit", "exit"}:
                    print("Exiting.")
                    sys.exit(0)
                v = int(v)
                if v < 0 or v > 3:
                    raise ValueError
                vals.append(v)
                break
            except ValueError:
                print("Please enter an integer 0–3, or 'q' to quit.")
    return np.array(vals, dtype=int).reshape(1, -1)

def predict(threshold=0.55):
    if not (os.path.exists(MODEL_PATH) and os.path.exists(LABELS_PATH)):
        print("Model not found. Run training first with --train.")
        sys.exit(1)

    pipe = joblib.load(MODEL_PATH)
    labels = np.load(LABELS_PATH, allow_pickle=True)

    x = ask_user_symptoms()
    probs = pipe.predict_proba(x)[0]
    best_idx = int(np.argmax(probs))
    best_label = labels[best_idx]
    best_prob = float(probs[best_idx])

    # Optionally abstain if not confident
    if best_prob < threshold:
        print(f"\nSuggested: ABSTAIN (low confidence {best_prob:.2f})")
        print("Top probabilities:")
        for i in np.argsort(-probs)[:3]:
            print(f"  {labels[i]}: {probs[i]:.2f}")
        return

    print(f"\nSuggested disease: {best_label} (prob={best_prob:.2f})")
    print("Top probabilities:")
    for i in np.argsort(-probs)[:3]:
        print(f"  {labels[i]}: {probs[i]:.2f}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--excel", type=str, default="medical_training.xlsx",
                    help="Path to Excel training data")
    ap.add_argument("--train", action="store_true", help="Train model from Excel")
    ap.add_argument("--predict", action="store_true", help="Run interactive prediction")
    ap.add_argument("--threshold", type=float, default=0.55, help="Abstain if max prob < threshold")
    args = ap.parse_args()

    if args.train:
        train(args.excel)
    if args.predict:
        predict(threshold=args.threshold)
    if not args.train and not args.predict:
        print("Nothing to do. Use --train and/or --predict. See --help.")

if __name__ == "__main__":
    main()
