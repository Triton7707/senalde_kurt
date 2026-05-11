from django.db import models


class PredictionResult(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    PREDICTION_CHOICES = [
        ('Low', 'Low Risk'),
        ('Medium', 'Medium Risk'),
        ('High', 'High Risk'),
    ]

    SLEEP_CHOICES = [
        ('Less than 5 hours', 'Less than 5 hours'),
        ('5-6 hours', '5-6 hours'),
        ('7-8 hours', '7-8 hours'),
        ('More than 8 hours', 'More than 8 hours'),
    ]

    age = models.IntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    academic_pressure = models.FloatField()
    sleep_duration = models.CharField(max_length=30, choices=SLEEP_CHOICES)
    cgpa = models.FloatField()
    study_satisfaction = models.FloatField()
    work_pressure = models.FloatField()
    prediction = models.CharField(max_length=10, choices=PREDICTION_CHOICES)
    prediction_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Prediction Result'
        verbose_name_plural = 'Prediction Results'

    def __str__(self):
        return f"Prediction #{self.id} — {self.prediction} Risk ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
