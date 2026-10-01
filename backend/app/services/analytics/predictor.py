import logging
import numpy as np
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class Predictor:
    """
    Enterprise ML Inference Engine.
    This service acts as the orchestration layer for trained scikit-learn/XGBoost models.
    """
    def __init__(self):
        # Mock Coefficient Matrices (Simulating trained weights)
        self.wait_time_weights = {
            "cardiology": 1.2, # Complex cases
            "pediatrics": 0.8, # Faster turnaround
            "orthopedics": 1.1,
            "general": 1.0
        }
        self.peak_hour_multipliers = {
            10: 1.5, # 10 AM Peak
            11: 1.6,
            14: 1.4,
            20: 0.7  # 8 PM Slow
        }

    def predict_wait_time(self, doctor_specialty: str, current_queue: int) -> int:
        """
        Simulates an XGBoost Regression inference.
        Formula: (Base * Specialty_Weight * Time_Multiplier * Queue_Depth)
        """
        base_unit = 12.0 # Minutes
        specialty_factor = self.wait_time_weights.get(doctor_specialty.lower(), 1.0)

        hour = datetime.now().hour
        peak_factor = self.peak_hour_multipliers.get(hour, 1.0)

        # Inference Logic
        predicted_wait = base_unit * specialty_factor * peak_factor * (current_queue or 1)

        # Add 5% safety margin for hospital operations
        final_prediction = int(predicted_wait * 1.05)

        logger.info(f"ML Inference | Specialty: {doctor_specialty} | Queue: {current_queue} | Predicted: {final_prediction}m")
        return final_prediction

    def triage_severity(self, symptoms: str, vitals: Dict[str, Any] = None) -> int:
        """
        Simulates a Random Forest Classification.
        Outputs a Severity Score from 1 (Critical) to 5 (Minor).
        """
        score = 5
        symptoms_lower = symptoms.lower()

        # High-weight features
        critical_indicators = ["unconscious", "stroke", "cardiac", "chest pain", "bleeding", "breathing"]
        urgent_indicators = ["fever", "fracture", "pain", "vomiting"]

        for indicator in critical_indicators:
            if indicator in symptoms_lower:
                score = min(score, 1)

        for indicator in urgent_indicators:
            if indicator in symptoms_lower:
                score = min(score, 3)

        # Numerical feature validation (Vitals)
        if vitals:
            bp_sys = vitals.get("bp_systolic", 120)
            if bp_sys > 180 or bp_sys < 80:
                score = 1

            pulse = vitals.get("pulse", 75)
            if pulse > 120 or pulse < 40:
                score = min(score, 2)

        return score

predictor = Predictor()
