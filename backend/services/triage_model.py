# backend/services/triage_model.py
"""
Triage inference service (severity + disease top-k).

- Loads artifacts once (thread-safe lazy load).
- Severity = soft-vote ensemble of RandomForest + XGBoost.
- Disease = multinomial LogisticRegression (optional; returns top-k).
- Default artifacts path: backend/artifacts/saca-triage-v1
  Override with env: MODEL_DIR=/absolute/path/to/saca-triage-v1

Expected files in MODEL_DIR:
  tfidf.pkl       # fitted TfidfVectorizer
  rf.pkl          # trained RandomForestClassifier
  xgb.pkl         # trained XGBClassifier
  disease.pkl     # (optional) trained LogisticRegression for disease
  config.json     # { "severity_labels": [...], "disease_labels": [...] }
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

import joblib
import numpy as np


# -----------------------
# Artifact directory
# -----------------------
_DEFAULT_ART_DIR = (
    Path(__file__).resolve().parent.parent / "artifacts" / "saca-triage-v1"
)
ART_DIR = Path(os.environ.get("MODEL_DIR", _DEFAULT_ART_DIR))


class _TriageModel:
    """Singleton loader + predictor."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._loaded = False
        self.tfidf = None
        self.rf = None
        self.xgb = None
        self.disease_clf = None
        self.sev_labels: List[str] = ["mild", "moderate", "severe"]
        self.dis_labels: Optional[List[str]] = None

    def load(self) -> None:
        """Load artifacts once (thread-safe)."""
        if self._loaded:
            return

        with self._lock:
            if self._loaded:
                return

            # Required
            tfidf_p = ART_DIR / "tfidf.pkl"
            rf_p = ART_DIR / "rf.pkl"
            xgb_p = ART_DIR / "xgb.pkl"
            cfg_p = ART_DIR / "config.json"

            # Optional
            disease_p = ART_DIR / "disease.pkl"

            if not tfidf_p.exists() or not rf_p.exists() or not xgb_p.exists():
                raise FileNotFoundError(
                    f"Missing required model files in {ART_DIR}. "
                    f"Expected tfidf.pkl, rf.pkl, xgb.pkl (and config.json)."
                )
            if not cfg_p.exists():
                # Backward compat: if no config, fall back to default labels
                cfg = {"severity_labels": self.sev_labels}
            else:
                cfg = json.loads(cfg_p.read_text())

            # load
            self.tfidf = joblib.load(tfidf_p)
            self.rf = joblib.load(rf_p)
            self.xgb = joblib.load(xgb_p)

            self.sev_labels = cfg.get("severity_labels", self.sev_labels)

            if disease_p.exists():
                self.disease_clf = joblib.load(disease_p)
                self.dis_labels = cfg.get("disease_labels")
            else:
                self.disease_clf = None
                self.dis_labels = None

            self._loaded = True

    # -----------------------
    # Public API
    # -----------------------
    def predict(
        self,
        text: str,
        *,
        topk_diseases: int = 3,
        return_probs: bool = True,
    ) -> Dict[str, Any]:
        """
        Predict triage severity (and optional disease top-k).

        Args:
          text: normalized English symptoms text.
          topk_diseases: how many diseases to return if disease model exists.
          return_probs: include raw severity probabilities.

        Returns:
          {
            "severity": "mild|moderate|severe",
            "confidence": float,
            "probs": [..]                      # if return_probs
            "disease_topk": [{"disease": str, "p": float}, ...]  # if available
          }
        """
        if not text or not isinstance(text, str):
            raise ValueError("text must be a non-empty string")

        if not self._loaded:
            self.load()

        # Transform
        X = self.tfidf.transform([text])

        # Severity: soft voting RF + XGB
        p_rf = self.rf.predict_proba(X)
        p_xgb = self.xgb.predict_proba(X)
        p_sev = (p_rf + p_xgb) / 2.0
        i = int(np.argmax(p_sev, axis=1)[0])
        sev = self.sev_labels[i]
        sev_conf = float(p_sev[0, i])

        result: Dict[str, Any] = {
            "severity": sev,
            "confidence": sev_conf,
        }
        if return_probs:
            result["probs"] = p_sev[0].tolist()

        # Disease top-k (optional)
        if self.disease_clf is not None and self.dis_labels:
            p_dis = self.disease_clf.predict_proba(X)[0]
            idx = np.argsort(p_dis)[::-1][: max(1, topk_diseases)]
            # ensure Python native types for JSON
            dis_labels = np.array(self.dis_labels, dtype=object)
            result["disease_topk"] = [
                {"disease": str(dis_labels[j]), "p": float(p_dis[j])} for j in idx
            ]

        return result

    def models_meta(self) -> Dict[str, Any]:
        """Small helper for debugging/versioning."""
        if not self._loaded:
            self.load()
        return {
            "artifact_dir": str(ART_DIR),
            "has_disease_model": self.disease_clf is not None,
            "severity_labels": self.sev_labels,
            "disease_labels": self.dis_labels,
        }


# -------- Singleton accessors --------
_model = _TriageModel()


def triage_predict(
    text: str, *, topk_diseases: int = 3, return_probs: bool = True
) -> Dict[str, Any]:
    """Convenience function for routes: single-text prediction."""
    return _model.predict(text, topk_diseases=topk_diseases, return_probs=return_probs)


def triage_meta() -> Dict[str, Any]:
    """Return model metadata (artifact path, labels, etc.)."""
    return _model.models_meta()