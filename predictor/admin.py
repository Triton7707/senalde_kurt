from django.contrib import admin
from .models import PredictionResult


@admin.register(PredictionResult)
class PredictionResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'age', 'gender', 'prediction', 'prediction_score', 'cgpa', 'created_at')
    list_filter = ('prediction', 'gender')
    search_fields = ('gender', 'prediction')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
