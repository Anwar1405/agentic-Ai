import os
import sys
import pickle
import json
from typing import Dict, Any, Optional
import numpy as np
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import Ridge
from sklearn.tree import DecisionTreeClassifier
from pathlib import Path

class ModelLoader:
    def __init__(self, model_dir: str = None):
        if model_dir is None:
            self.model_dir = Path("dataset")
        else:
            self.model_dir = Path(model_dir)
        
        self._cache = {}
    
    def load_model(self, model_path: str):
        full_path = self.model_dir / model_path
        if full_path in self._cache:
            return self._cache[full_path]
        
        if not full_path.exists():
            raise FileNotFoundError(f"Model file not found: {full_path}")
        
        with open(full_path, 'rb') as f:
            model = pickle.load(f)
        
        self._cache[full_path] = model
        return model
    
    def load_climate_model(self):
        try:
            return self.load_model("CLIMATE Agent models/saved_models/random_forest_climate_agent.pkl")
        except Exception:
            try:
                return self.load_model("CLIMATE Agent models/random_forest_climate_model.pkl")
            except Exception:
                try:
                    return self.load_model("CLIMATE Agent models/stable_rf_model.pkl")
                except Exception:
                    return None
    
    def load_economic_model(self):
        # Try multiple paths
        paths = [
            "ECONOMIC AGENT models/best_ridge_model.pkl",
            "ECONOMIC AGENT models/checking UI/best_ridge_model.pkl",
        ]
        
        for path in paths:
            try:
                model = self.load_model(path)
                if model is not None:
                    return model
            except Exception:
                continue
        
        # If all fail, return None - will use formula
        return None
    
    def load_welfare_model(self):
        try:
            return self.load_model("CLIMATE Agent models/saved_models/random_forest_climate_agent.pkl")
        except Exception:
            try:
                return self.load_model("CLIMATE Agent models/stable_rf_model.pkl")
            except Exception:
                return None
    
    def load_feature_columns(self):
        try:
            return self.load_model("CLIMATE Agent models/saved_models/feature_columns.pkl")
        except Exception:
            return None
    
    def get_feature_importance(self, model, feature_names):
        if isinstance(model, RandomForestClassifier):
            return model.feature_importances_
        elif isinstance(model, Ridge):
            return model.coef_
        elif isinstance(model, DecisionTreeClassifier):
            return model.feature_importances_
        else:
            return None
    
    def get_shap_explanation(self, model, input_data, feature_names):
        if not feature_names:
            return None
        
        try:
            if isinstance(model, RandomForestClassifier):
                explainer = shap.TreeExplainer(model)
            elif isinstance(model, Ridge):
                explainer = shap.LinearExplainer(model, input_data)
            elif isinstance(model, DecisionTreeClassifier):
                explainer = shap.TreeExplainer(model)
            else:
                return None
            
            shap_values = explainer.shap_values(input_data)
            
            explanation = {}
            for i, name in enumerate(feature_names):
                if isinstance(shap_values, list):
                    value = shap_values[0][i] if len(shap_values) > 0 else 0
                else:
                    value = shap_values[i]
                explanation[name] = float(value)
            
            return explanation
        except Exception:
            return None
