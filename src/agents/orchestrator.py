from typing import Dict, Any, Optional
from .base_agent import BaseAgent, AgentResult
from .crewai_orchestrator import CrewAIOrchestrator
from ..utils.data_loader import DataLoader
from ..utils.model_loader import ModelLoader
import json

class MainOrchestrator(BaseAgent):
    def __init__(self, data_loader: DataLoader = None):
        super().__init__("Main Orchestrator", data_loader)
        self.crewai_orchestrator = CrewAIOrchestrator(data_loader if data_loader else DataLoader())
        self.model_loader = ModelLoader()
    
    def process(self, application_data: Dict[str, Any]) -> AgentResult:
        crewai_result = self.crewai_orchestrator.process(application_data)
        
        if crewai_result.status == "REJECT" or crewai_result.status == "REVIEW":
            return crewai_result
        
        try:
            shap_explanations = self.crewai_orchestrator.generate_shap_explanations(
                crewai_result.result.get("agent_results", {})
            )
            
            crewai_result.result["shap_explanations"] = shap_explanations
        except Exception as e:
            crewai_result.result["shap_explanations"] = {"error": str(e)}
        
        return crewai_result