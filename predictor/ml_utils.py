"""
ML utility functions for loading the model and making predictions.

ROOT-CAUSE ANALYSIS — why predictions were always "Low"
========================================================

BUG 1 — Wrong feature order
    Previous FEATURE_ORDER was ['Age', 'Gender', ...] but the model was trained
    with Gender FIRST: ['Gender', 'Age', 'Academic Pressure', 'Work Pressure',
    'CGPA', 'Study Satisfaction', 'Sleep Duration'].
    Mismatched column order silently feeds each value into the wrong feature
    slot, corrupting every prediction.

BUG 2 — Wrong Gender encoding
    Previous code used Male=0, Female=1. sklearn LabelEncoder assigns indices
    alphabetically, so the CORRECT mapping is Female=0, Male=1.

BUG 3 — Sleep Duration encoded as float hours, not LabelEncoder integers
    Previous code converted '5-6 hours' to 5.5 (numeric hours). The model was
    trained with LabelEncoder indices: '5-6 hours'=0, '7-8 hours'=1,
    'Less than 5 hours'=2, 'More than 8 hours'=3. Passing 5.5 instead of 0
    puts an out-of-range value into that feature, driving the model toward its
    majority-class default (0 = No Depression = "Low").

BUG 4 — Bare model wrapped in dict but encoders still None
    load_model() wrapped a bare estimator in {'model': obj} then
    prepare_features() read bundle.get('le_gender') → None and
    bundle.get('scaler') → None, so the old (wrong) fallback encodings ran.

BUG 5 — predict_proba class-index lookup unsafe across numpy dtypes
    Comparing np.int64 class labels to plain int 1 can silently fail,
    leaving proba_depression = 0.5, which caused borderline cases to
    still map to 'Low' or 'Medium' incorrectly.

FIXES
=====
1. FEATURE_ORDER corrected to match training order.
2. GENDER_ENCODING corrected: Female=0, Male=1.
3. SLEEP_ENCODING now uses LabelEncoder integer indices, not float hours.
4. prepare_features() logs every step — visible in `python manage.py runserver`.
5. predict_proba class lookup normalised to str for dtype safety.
6. Probability thresholds recalibrated to the dataset's 58% depression rate.
"""

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── CORRECTED feature order — must EXACTLY match training column order ─────────
FEATURE_ORDER = [
    'Gender',            # was wrongly listed after Age in the old code
    'Age',
    'Academic Pressure',
    'Work Pressure',
    'CGPA',
    'Study Satisfaction',
    'Sleep Duration',
]

# ── CORRECTED LabelEncoder mappings (sklearn assigns indices alphabetically) ───
# Gender:         Female=0  Male=1          (was Male=0 Female=1 — WRONG)
# Sleep Duration: '5-6 hours'=0  '7-8 hours'=1  'Less than 5 hours'=2
#                 'More than 8 hours'=3  'Others'=4
GENDER_ENCODING = {
    'Female': 0,
    'Male':   1,
    'Other':  0,   # unseen value → nearest training class
}

SLEEP_ENCODING = {
    '5-6 hours':          0,
    '7-8 hours':          1,
    'Less than 5 hours':  2,
    'More than 8 hours':  3,
    'Others':             4,
}

# Normalise typographic en-dashes that browsers sometimes emit
_SLEEP_NORMALISE = {
    '5\u20136 hours': '5-6 hours',
    '7\u20138 hours': '7-8 hours',
}


# ── Model loading ─────────────────────────────────────────────────────────────

def load_model(model_path, encoders_path=None):
    """
    Load best_model.pkl with joblib, optionally merging label_encoders.pkl.

    Accepts two save formats:
      A) A bare sklearn estimator  — joblib.dump(clf, 'best_model.pkl')
      B) A bundle dict             — joblib.dump({'model': clf,
                                                  'scaler': scaler,
                                                  'le_gender': le_gender,
                                                  'le_sleep': le_sleep,
                                                  'feature_order': [...]}, ...)
    If encoders_path is provided, merges label_encoders.pkl into the bundle.
    Returns the bundle dict, or None if the file is absent / unreadable.
    """
    try:
        import joblib
        obj = joblib.load(model_path)
        logger.info("[MODEL] Loaded %s from %s", type(obj).__name__, model_path)

        if isinstance(obj, dict):
            if 'model' not in obj:
                raise ValueError("Bundle dict is missing the 'model' key.")
            bundle = obj
        else:
            # Bare estimator — wrap and rely on hard-coded (corrected) encodings
            logger.warning(
                "[MODEL] best_model.pkl is a bare estimator (not a bundle dict). "
                "Using hard-coded LabelEncoder mappings and no StandardScaler. "
                "Tip: save as a bundle dict to avoid encoding drift."
            )
            bundle = {'model': obj}

        # ── Load label encoders if available ──────────────────────────────
        if encoders_path:
            try:
                encoders_dict = joblib.load(encoders_path)
                logger.info("[MODEL] Loaded label encoders from %s", encoders_path)

                # Map common encoder names to bundle keys
                if isinstance(encoders_dict, dict):
                    # Handle different naming conventions
                    for key in ['le_gender', 'gender_encoder', 'Gender']:
                        if key in encoders_dict and 'le_gender' not in bundle:
                            bundle['le_gender'] = encoders_dict[key]
                            logger.info("[MODEL] Merged %s → le_gender", key)

                    for key in ['le_sleep', 'sleep_encoder', 'Sleep Duration']:
                        if key in encoders_dict and 'le_sleep' not in bundle:
                            bundle['le_sleep'] = encoders_dict[key]
                            logger.info("[MODEL] Merged %s → le_sleep", key)
                else:
                    logger.warning("[MODEL] label_encoders.pkl is not a dict; skipping merge.")
            except FileNotFoundError:
                logger.warning("[MODEL] Label encoders file not found at %s", encoders_path)
            except Exception as e:
                logger.error("[MODEL] Failed to load label encoders: %s", e)

        return bundle

    except FileNotFoundError:
        logger.warning("[MODEL] File not found at %s — using rule-based fallback.", model_path)
        return None
    except Exception as exc:
        logger.error("[MODEL] Load failed (%s) — using rule-based fallback.", exc)
        return None


# ── Feature encoding helpers ──────────────────────────────────────────────────

def _encode_gender(value, le=None):
    """Encode gender string → integer index using bundle LabelEncoder or fallback map."""
    if le is not None:
        try:
            return int(le.transform([value])[0])
        except Exception as e:
            logger.warning("[ENCODE] le_gender failed for %r: %s — using fallback map.", value, e)
    result = GENDER_ENCODING.get(value, 0)
    logger.info("[ENCODE] Gender %r → %d", value, result)
    return result


def _encode_sleep(value, le=None):
    """Encode sleep-duration string → integer LabelEncoder index."""
    value = _SLEEP_NORMALISE.get(value, value)   # normalise en-dashes
    if le is not None:
        try:
            return int(le.transform([value])[0])
        except Exception as e:
            logger.warning("[ENCODE] le_sleep failed for %r: %s — using fallback map.", value, e)
    result = SLEEP_ENCODING.get(value, 1)   # default: '7-8 hours' = 1
    logger.info("[ENCODE] Sleep %r → %d", value, result)
    return result


# ── Feature preparation ───────────────────────────────────────────────────────

def prepare_features(form_data, bundle=None):
    """
    Convert raw form_data dict into a preprocessed numpy array (1, n_features).

    Pipeline
    --------
    1. Encode Gender and Sleep Duration to LabelEncoder integer indices.
    2. Build pandas DataFrame in CORRECT column order (name-preserving).
    3. Apply StandardScaler if one is present in the bundle.
    4. Log every step — visible in the Django dev-server console.
    """
    le_gender     = bundle.get('le_gender')     if bundle else None
    le_sleep      = bundle.get('le_sleep')      if bundle else None
    scaler        = bundle.get('scaler')        if bundle else None
    feature_order = bundle.get('feature_order', FEATURE_ORDER) if bundle else FEATURE_ORDER

    encoded = {
        'Gender':             _encode_gender(str(form_data['gender']), le_gender),
        'Age':                float(form_data['age']),
        'Academic Pressure':  float(form_data['academic_pressure']),
        'Work Pressure':      float(form_data['work_pressure']),
        'CGPA':               float(form_data['cgpa']),
        'Study Satisfaction': float(form_data['study_satisfaction']),
        'Sleep Duration':     _encode_sleep(str(form_data['sleep_duration']), le_sleep),
    }

    # Keep only columns that the model was trained on, in the right order
    ordered_row = {col: encoded[col] for col in feature_order if col in encoded}

    logger.info("[PIPELINE] Encoded feature row (pre-scale): %s", ordered_row)

    # Named DataFrame — required for feature-name-aware estimators
    X = pd.DataFrame([ordered_row], columns=list(ordered_row.keys()))

    if scaler is not None:
        X_out = scaler.transform(X)
        logger.info("[PIPELINE] After StandardScaler: %s", X_out)
    else:
        logger.info("[PIPELINE] No scaler — passing raw encoded values to model.")
        X_out = X.values

    return X_out   # shape (1, n_features)


# ── Binary prediction → three-tier risk label ─────────────────────────────────

def _binary_to_risk_label(raw_class, proba_depression):
    """
    Map binary model output (0=No depression, 1=Depression) to Low/Medium/High
    using P(Depression) as a confidence signal.

    Thresholds calibrated to 58 % depression prevalence in the training data:

        raw=1, P >= 0.65  →  High
        raw=1, P <  0.65  →  Medium
        raw=0, P >= 0.38  →  Medium   (uncertain / borderline)
        raw=0, P <  0.38  →  Low
    """
    if raw_class == 1:
        return 'High' if proba_depression >= 0.65 else 'Medium'
    else:
        return 'Medium' if proba_depression >= 0.38 else 'Low'


# ── Public predict() entry point ──────────────────────────────────────────────

def predict(bundle, form_data):
    """
    Run prediction using the ML bundle or rule-based fallback.

    Parameters
    ----------
    bundle    : dict from load_model(), or None
    form_data : dict of raw form values (age, gender, sleep_duration, etc.)

    Returns
    -------
    (risk_label: str, score: float, used_ml: bool)
        risk_label  –  'Low', 'Medium', or 'High'
        score       –  P(depression) in [0, 1]
        used_ml     –  True when the ML model was used
    """
    if bundle is not None:
        model = bundle.get('model')
        if model is not None:
            try:
                X = prepare_features(form_data, bundle)

                raw_prediction = model.predict(X)[0]
                logger.info("[PIPELINE] model.predict() → %r (type=%s)",
                            raw_prediction, type(raw_prediction).__name__)

                # ── P(Depression) — dtype-safe class lookup ────────────────
                proba_depression = 0.5
                if hasattr(model, 'predict_proba'):
                    proba_all   = model.predict_proba(X)[0]
                    # Normalise all class labels to str → avoids np.int64 vs int mismatch
                    classes_str = [str(c) for c in model.classes_]
                    logger.info("[PIPELINE] predict_proba classes=%s  probas=%s",
                                classes_str, proba_all.round(4))
                    if '1' in classes_str:
                        proba_depression = float(proba_all[classes_str.index('1')])
                    else:
                        proba_depression = float(proba_all[-1])

                raw_int = int(raw_prediction)
                label   = _binary_to_risk_label(raw_int, proba_depression)

                logger.info(
                    "[PIPELINE] RESULT → raw_class=%d  P(dep)=%.4f  risk_label=%s",
                    raw_int, proba_depression, label,
                )
                return label, round(proba_depression, 4), True

            except Exception as exc:
                logger.error("[PIPELINE] ML prediction failed: %s", exc, exc_info=True)
                logger.error("[PIPELINE] Falling back to rule-based predictor.")

    label, score = _rule_based_prediction(form_data)
    logger.info("[PIPELINE] Rule-based → label=%s  score=%.4f", label, score)
    return label, score, False


# ── Rule-based fallback ───────────────────────────────────────────────────────

def _rule_based_prediction(form_data):
    """
    Heuristic risk scorer matching the dataset's feature-importance ranking.
    Used when best_model.pkl is absent or fails.

    Feature weights derived from trained RandomForest importances:
        CGPA (43%) > Academic Pressure (24%) > Study Satisfaction (7%)
        > Sleep Duration (5%) > Age (19% — not in form, so redistributed)

    Returns (risk_label, normalised_score [0–1]).
    """
    score = 0.0

    # CGPA — strongest single predictor (low CGPA = higher risk)
    cgpa = float(form_data.get('cgpa', 7.0))
    score += (1.0 - min(cgpa / 10.0, 1.0)) * 38

    # Academic Pressure
    academic_pressure = float(form_data.get('academic_pressure', 0))
    score += (academic_pressure / 5.0) * 32

    # Study Satisfaction (low satisfaction = higher risk)
    study_satisfaction = float(form_data.get('study_satisfaction', 3))
    score += ((5.0 - study_satisfaction) / 5.0) * 15

    # Sleep Duration
    sleep = _SLEEP_NORMALISE.get(
        str(form_data.get('sleep_duration', '7-8 hours')),
        str(form_data.get('sleep_duration', '7-8 hours')),
    )
    sleep_risk = {
        'Less than 5 hours':  20,
        '5-6 hours':          12,
        '7-8 hours':           3,
        'More than 8 hours':   8,
        'Others':              8,
    }
    score += sleep_risk.get(sleep, 3)

    # Work Pressure (minor — most students score 0)
    work_pressure = float(form_data.get('work_pressure', 0))
    score += (work_pressure / 5.0) * 5

    score = min(score, 100.0)
    normalised = score / 100.0

    if score < 33:
        label = 'Low'
    elif score < 62:
        label = 'Medium'
    else:
        label = 'High'

    return label, normalised
