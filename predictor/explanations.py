"""
Rule-based explanation and recommendation engine for depression risk predictions.
"""


def generate_explanation(form_data, prediction):
    """
    Generate a plain-language explanation of the prediction
    based on the student's input values.
    """
    factors = []
    protective = []

    academic_pressure = float(form_data.get('academic_pressure', 0))
    work_pressure = float(form_data.get('work_pressure', 0))
    sleep = form_data.get('sleep_duration', '7-8 hours')
    study_satisfaction = float(form_data.get('study_satisfaction', 3))
    cgpa = float(form_data.get('cgpa', 7.0))

    # Risk factors
    if academic_pressure >= 4:
        factors.append("very high academic pressure (rated {:.1f}/5)".format(academic_pressure))
    elif academic_pressure >= 3:
        factors.append("moderate-to-high academic pressure (rated {:.1f}/5)".format(academic_pressure))

    if work_pressure >= 4:
        factors.append("very high work pressure (rated {:.1f}/5)".format(work_pressure))
    elif work_pressure >= 3:
        factors.append("notable work pressure (rated {:.1f}/5)".format(work_pressure))

    if sleep == 'Less than 5 hours':
        factors.append("severely insufficient sleep (less than 5 hours)")
    elif sleep == '5-6 hours':
        factors.append("below-recommended sleep duration (5–6 hours)")

    if study_satisfaction <= 2:
        factors.append("low study satisfaction (rated {:.1f}/5)".format(study_satisfaction))

    if cgpa < 5.0:
        factors.append("low academic performance (CGPA {:.2f})".format(cgpa))

    # Protective factors
    if academic_pressure <= 2:
        protective.append("manageable academic workload")
    if sleep in ('7-8 hours', 'More than 8 hours') and sleep != 'More than 8 hours':
        protective.append("healthy sleep duration")
    if study_satisfaction >= 4:
        protective.append("high study satisfaction")
    if cgpa >= 7.5:
        protective.append("strong academic performance")
    if work_pressure <= 1:
        protective.append("low work-related stress")

    # Build explanation
    lines = []
    if prediction == 'Low':
        lines.append(
            "Based on your inputs, your depression risk profile appears <strong>low</strong>. "
            "Your overall stress indicators are within manageable ranges."
        )
    elif prediction == 'Medium':
        lines.append(
            "Based on your inputs, you show <strong>moderate</strong> indicators associated with "
            "student depression. Some areas in your life may be contributing to stress."
        )
    else:
        lines.append(
            "Based on your inputs, several key indicators suggest an <strong>elevated</strong> risk "
            "of depression. This is not a diagnosis — please consider speaking with a professional."
        )

    if factors:
        lines.append(
            "<strong>Key risk factors identified:</strong> " + "; ".join(f.capitalize() for f in factors) + "."
        )

    if protective:
        lines.append(
            "<strong>Protective factors:</strong> " + "; ".join(f.capitalize() for f in protective) + "."
        )

    return lines


def generate_recommendations(prediction, form_data):
    """
    Return a list of personalised, actionable recommendations
    based on the prediction and form inputs.
    """
    sleep = form_data.get('sleep_duration', '7-8 hours')
    academic_pressure = float(form_data.get('academic_pressure', 0))
    work_pressure = float(form_data.get('work_pressure', 0))
    study_satisfaction = float(form_data.get('study_satisfaction', 3))

    recs = []

    # Sleep recommendations
    if sleep in ('Less than 5 hours', '5-6 hours'):
        recs.append({
            'icon': '🌙',
            'title': 'Prioritise Sleep',
            'detail': (
                'Aim for 7–9 hours of quality sleep per night. '
                'Set a consistent bedtime, avoid screens 30 minutes before sleep, '
                'and limit caffeine intake after 2 PM.'
            )
        })

    # Academic pressure
    if academic_pressure >= 3:
        recs.append({
            'icon': '📚',
            'title': 'Manage Academic Stress',
            'detail': (
                'Break large tasks into smaller, manageable chunks using a planner. '
                'Practice the Pomodoro technique (25 min study / 5 min break). '
                'Speak to your academic advisor if deadlines feel overwhelming.'
            )
        })

    # Work pressure
    if work_pressure >= 3:
        recs.append({
            'icon': '💼',
            'title': 'Balance Work and Study',
            'detail': (
                'Consider reducing work hours during exam periods. '
                'Communicate with your employer about your academic commitments. '
                'Set firm boundaries to protect study and rest time.'
            )
        })

    # Study satisfaction
    if study_satisfaction <= 2:
        recs.append({
            'icon': '🎯',
            'title': 'Reconnect with Your Purpose',
            'detail': (
                'Reflect on why you chose your field. Connect with peers or mentors who inspire you. '
                'Explore elective subjects that genuinely interest you. '
                'Consider speaking to a career counsellor if you feel misaligned with your degree.'
            )
        })

    # Social connection
    if prediction in ('Medium', 'High'):
        recs.append({
            'icon': '🤝',
            'title': 'Stay Socially Connected',
            'detail': (
                'Regular social interaction is a powerful buffer against depression. '
                'Join a student club, study group, or community activity. '
                'Schedule regular catch-ups with friends or family.'
            )
        })

    # Physical activity
    recs.append({
        'icon': '🏃',
        'title': 'Move Your Body Daily',
        'detail': (
            'Even 20–30 minutes of moderate exercise (walking, cycling, yoga) '
            'significantly reduces stress hormones and boosts mood-regulating neurotransmitters. '
            'Try to make it a non-negotiable part of your routine.'
        )
    })

    # Professional help for high risk
    if prediction == 'High':
        recs.append({
            'icon': '🧠',
            'title': 'Seek Professional Support',
            'detail': (
                'Your results suggest significant stress. Please consider reaching out to your '
                "university's student counselling service, a GP, or a mental health professional. "
                'Seeking help is a sign of strength, not weakness. You don\'t have to navigate this alone.'
            )
        })

    # Mindfulness for all
    recs.append({
        'icon': '🧘',
        'title': 'Practice Mindfulness',
        'detail': (
            'Even 5–10 minutes of daily mindfulness or meditation can reduce anxiety and improve focus. '
            'Apps like Headspace, Calm, or simply guided breathing exercises on YouTube are great starting points.'
        )
    })

    return recs
