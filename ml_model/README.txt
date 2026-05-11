Place your trained model file here:

    ml_model/best_model.pkl

The model must be serialized with joblib and accept a 2D numpy array with shape (1, 7)
in the following column order:

    [age, gender_encoded, academic_pressure, sleep_hours, cgpa, study_satisfaction, work_pressure]

Where:
  - gender_encoded : Male=0, Female=1, Other=2
  - sleep_hours    : numeric hours (4.0 / 5.5 / 7.5 / 9.0)
  - All other fields are raw floats from the form.

If the model file is missing, the system automatically falls back to a rule-based predictor.
