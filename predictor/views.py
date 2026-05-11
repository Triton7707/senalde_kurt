import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings

from .forms import PredictionForm
from .models import PredictionResult
from .ml_utils import load_model, predict
from .explanations import generate_explanation, generate_recommendations

logger = logging.getLogger(__name__)

# ── Model bundle singleton ─────────────────────────────────────────────────────
# Loaded once per Django process, reused across every request.
# If best_model.pkl is missing, _bundle stays None and ml_utils.predict()
# automatically falls back to the rule-based predictor.
_bundle = None
_bundle_loaded = False


def get_bundle():
    """Lazy-load the model bundle (loaded once per process, then cached)."""
    global _bundle, _bundle_loaded
    if not _bundle_loaded:
        _bundle = load_model(
            settings.ML_MODEL_PATH,
            encoders_path=settings.ML_ENCODERS_PATH
        )
        _bundle_loaded = True
        if _bundle is None:
            logger.warning(
                "[VIEW] best_model.pkl not found or failed to load. "
                "The rule-based fallback predictor will be used instead."
            )
        else:
            logger.info("[VIEW] Model bundle ready.")
    return _bundle


def home(request):
    """
    GET  → Render the student input form.
    POST → Validate form, run prediction pipeline, save to DB, redirect to result.
    """
    if request.method == 'POST':
        form = PredictionForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            # ── Build form_data dict (all raw values as strings/numbers) ──────
            form_data = {
                'age':                data['age'],
                'gender':             data['gender'],
                'academic_pressure':  data['academic_pressure'],
                'sleep_duration':     data['sleep_duration'],
                'cgpa':               data['cgpa'],
                'study_satisfaction': data['study_satisfaction'],
                'work_pressure':      data['work_pressure'],
            }

            logger.info("[VIEW] Raw form submission: %s", form_data)

            # ── Run prediction ─────────────────────────────────────────────────
            bundle = get_bundle()
            label, score, used_ml = predict(bundle, form_data)

            logger.info(
                "[VIEW] Prediction complete — label=%s  score=%.4f  used_ml=%s",
                label, score, used_ml,
            )

            # ── Persist to DB ──────────────────────────────────────────────────
            result_obj = PredictionResult.objects.create(
                age=data['age'],
                gender=data['gender'],
                academic_pressure=data['academic_pressure'],
                sleep_duration=data['sleep_duration'],
                cgpa=data['cgpa'],
                study_satisfaction=data['study_satisfaction'],
                work_pressure=data['work_pressure'],
                prediction=label,
                prediction_score=round(score, 4),
            )

            return redirect('result', pk=result_obj.pk)

    else:
        form = PredictionForm()

    return render(request, 'predictor/home.html', {'form': form})


def result(request, pk):
    """Display the prediction result page with explanation and recommendations."""
    result_obj = get_object_or_404(PredictionResult, pk=pk)

    form_data = {
        'age':                result_obj.age,
        'gender':             result_obj.gender,
        'academic_pressure':  result_obj.academic_pressure,
        'sleep_duration':     result_obj.sleep_duration,
        'cgpa':               result_obj.cgpa,
        'study_satisfaction': result_obj.study_satisfaction,
        'work_pressure':      result_obj.work_pressure,
    }

    explanation_lines = generate_explanation(form_data, result_obj.prediction)
    recommendations   = generate_recommendations(result_obj.prediction, form_data)

    risk_meta = {
        'Low': {
            'color':   '#22c55e',
            'bg':      '#f0fdf4',
            'border':  '#bbf7d0',
            'badge':   'LOW RISK',
            'emoji':   '✅',
            'message': (
                "Great news — your current indicators suggest a low depression risk. "
                "Keep maintaining your healthy habits."
            ),
        },
        'Medium': {
            'color':   '#f59e0b',
            'bg':      '#fffbeb',
            'border':  '#fde68a',
            'badge':   'MEDIUM RISK',
            'emoji':   '⚠️',
            'message': (
                "Some stress indicators are elevated. Review the recommendations below "
                "and consider talking to someone you trust."
            ),
        },
        'High': {
            'color':   '#ef4444',
            'bg':      '#fef2f2',
            'border':  '#fecaca',
            'badge':   'HIGH RISK',
            'emoji':   '🔴',
            'message': (
                "Multiple risk factors are present. Please consider reaching out to a "
                "counsellor or mental health professional."
            ),
        },
    }

    meta          = risk_meta.get(result_obj.prediction, risk_meta['Medium'])
    score_percent = int(result_obj.prediction_score * 100)

    context = {
        'result':            result_obj,
        'explanation_lines': explanation_lines,
        'recommendations':   recommendations,
        'meta':              meta,
        'score_percent':     score_percent,
    }
    return render(request, 'predictor/result.html', context)


def history(request):
    """Show paginated table of all past predictions with summary statistics."""
    all_results = PredictionResult.objects.all()

    page     = max(1, int(request.GET.get('page', 1)))
    per_page = 10
    total    = all_results.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page     = min(page, total_pages)
    start    = (page - 1) * per_page
    end      = start + per_page

    context = {
        'results':      all_results[start:end],
        'total':        total,
        'page':         page,
        'total_pages':  total_pages,
        'has_prev':     page > 1,
        'has_next':     page < total_pages,
        'low_count':    all_results.filter(prediction='Low').count(),
        'medium_count': all_results.filter(prediction='Medium').count(),
        'high_count':   all_results.filter(prediction='High').count(),
    }
    return render(request, 'predictor/history.html', context)


def delete_result(request, pk):
    """Delete a single prediction record (POST only for CSRF protection)."""
    if request.method == 'POST':
        get_object_or_404(PredictionResult, pk=pk).delete()
    return redirect('history')
