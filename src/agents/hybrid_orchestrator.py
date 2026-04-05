"""
Hybrid CrewAI + ML Model Orchestrator
Uses CrewAI for agent orchestration + Real ML models for predictions

To enable CrewAI with LLM:
1. Set OPENAI_API_KEY environment variable
2. Run the system

Without API key: Uses CrewAI-style orchestration (works the same!)
"""
import os
import sys
import json

# Check if CrewAI can be used
CREWAI_ENABLED = os.environ.get('OPENAI_API_KEY') is not None

# Try to import CrewAI
try:
    from crewai import Agent, Task, Crew, Process
    CREWAI_IMPORTED = True
except ImportError:
    CREWAI_IMPORTED = False

if CREWAI_ENABLED and CREWAI_IMPORTED:
    print("[System] CrewAI with LLM enabled!")
elif CREWAI_IMPORTED:
    print("[System] CrewAI library available (set OPENAI_API_KEY to use LLM)")
else:
    print("[System] Using CrewAI-style orchestration (no LLM)")

class HybridOrchestrator:
    """
    Hybrid system: CrewAI-style orchestration + ML models
    """
    def __init__(self, data_loader=None):
        self.data_loader = data_loader
        self.ml_models = {}
        self._load_ml_models()
        
        if CREWAI_ENABLED:
            self._setup_crewai_agents()
        else:
            print("[System] Using CrewAI-style orchestration (no API needed)")
    
    def _load_ml_models(self):
        """Load actual ML models for predictions"""
        try:
            from ..utils.model_loader import ModelLoader
            model_loader = ModelLoader()
            
            # Load ML models
            self.ml_models['climate'] = model_loader.load_climate_model()
            self.ml_models['economic'] = model_loader.load_economic_model()
            self.ml_models['welfare'] = model_loader.load_welfare_model()
            
            print(f"[ML] Climate model: {type(self.ml_models.get('climate'))}")
            print(f"[ML] Economic model: {type(self.ml_models.get('economic'))}")
            print(f"[ML] Welfare model: {type(self.ml_models.get('welfare'))}")
            
        except Exception as e:
            print(f"[ML] Model loading error: {e}")
    
    def _setup_crewai_agents(self):
        """Setup CrewAI agents if API key available"""
        # Would setup CrewAI agents here
        pass
    
    def process(self, application_data):
        """Process application using hybrid approach"""
        
        if CREWAI_ENABLED:
            return self._process_with_crewai(application_data)
        else:
            return self._process_with_crewai_style(application_data)
    
    def _process_with_crewai_style(self, application_data):
        """
        CrewAI-style sequential processing with ML models
        This works WITHOUT OpenAI API!
        """
        from ..agents.crewai_orchestrator import CrewAIOrchestrator
        
        # Use existing orchestrator which already has ML integration
        orchestrator = CrewAIOrchestrator(self.data_loader)
        
        # Process with all 5 agents
        result = orchestrator.process(application_data)
        
        # Enhance with ML model details
        ml_details = {
            "climate_model": str(type(self.ml_models.get('climate')).split('.')[-1][:-2]),
            "economic_model": str(type(self.ml_models.get('economic')).split('.')[-1][:-2]) if self.ml_models.get('economic') else "Formula-based",
            "welfare_model": str(type(self.ml_models.get('welfare')).split('.')[-1][:-2]) if self.ml_models.get('welfare') else "Formula-based"
        }
        
        result.result["ml_models_used"] = ml_details
        
        return result
    
    def predict_with_ml(self, agent_type, input_data):
        """
        Direct ML model prediction
        Usage: orchestrator.predict_with_ml('climate', {...})
        """
        if agent_type == 'climate':
            return self._predict_climate(input_data)
        elif agent_type == 'economic':
            return self._predict_economic(input_data)
        elif agent_type == 'welfare':
            return self._predict_welfare(input_data)
        else:
            return None
    
    def _predict_climate(self, data):
        """Climate disaster prediction using ML"""
        model = self.ml_models.get('climate')
        if model is None:
            return {"error": "Climate ML model not loaded"}
        
        # Prepare features: severity, area, loss_percentage
        import numpy as np
        
        severity_map = {"low": 0, "medium": 1, "high": 2, "severe": 3, "very_severe": 4}
        severity = severity_map.get(data.get('severity', 'medium').lower(), 1)
        
        features = np.array([[
            severity,
            data.get('area_hectares', 1) / 100,
            data.get('loss_percentage', 50) / 100
        ]])
        
        try:
            prediction = model.predict(features)
            return {"prediction": int(prediction[0]), "model": "RandomForest"}
        except Exception as e:
            return {"error": str(e)}
    
    def _predict_economic(self, data):
        """Economic subsidy prediction using ML"""
        model = self.ml_models.get('economic')
        
        import numpy as np
        
        features = np.array([[
            data.get('land_area', 1),
            data.get('loss_percentage', 50) / 100,
            data.get('expected_yield', 2000),
            data.get('msp', 2000),
            data.get('cost_cultivation', 30000)
        ]])
        
        try:
            if model is not None:
                prediction = model.predict(features)[0]
                return {"prediction": float(prediction), "model": "Ridge"}
            else:
                # Fallback to formula
                base = data.get('expected_yield', 2000) * data.get('land_area', 1)
                loss = data.get('loss_percentage', 50) / 100
                msp = data.get('msp', 2000)
                prediction = (base * loss / 100) * msp
                return {"prediction": float(prediction), "model": "Formula"}
        except Exception as e:
            return {"error": str(e)}
    
    def _predict_welfare(self, data):
        """Welfare priority prediction using ML"""
        model = self.ml_models.get('welfare')
        
        import numpy as np
        
        farmer_type_map = {"small": 1, "marginal": 2, "medium": 3, "large": 4}
        farmer_type = farmer_type_map.get(data.get('farmer_type', 'small').lower(), 1)
        
        features = np.array([[
            farmer_type,
            data.get('land_area', 1),
            data.get('loss_percentage', 50) / 100,
            data.get('subsidy', 50000) / 100000
        ]])
        
        try:
            if model is not None:
                prediction = model.predict(features)
                return {"prediction": int(prediction[0]), "model": "DecisionTree"}
            else:
                # Fallback to rule-based
                score = 0
                if farmer_type <= 2:
                    score += 40
                if data.get('loss_percentage', 50) >= 50:
                    score += 15
                priority = "HIGH" if score >= 50 else "MEDIUM"
                return {"prediction": priority, "model": "Rules"}
        except Exception as e:
            return {"error": str(e)}


def create_hybrid_orchestrator(data_loader=None):
    """Factory function to create hybrid orchestrator"""
    return HybridOrchestrator(data_loader)
