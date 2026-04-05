from typing import Dict, Any, List, Optional
import json
import numpy as np
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import Ridge
from sklearn.tree import DecisionTreeClassifier
from .base_agent import BaseAgent, AgentResult
from .policy_agent import PolicyAgent
from .legal_agent import LegalAgent
from .climate_agent import ClimateAgent
from .agri_economic_agent import AgriEconomicAgent
from .welfare_agent import WelfareAgent
from ..utils.model_loader import ModelLoader
from ..utils.data_loader import DataLoader

class CrewAIOrchestrator(BaseAgent):
    def __init__(self, data_loader: DataLoader = None):
        super().__init__("CrewAI Orchestrator", data_loader)
        self.model_loader = ModelLoader()
        self.agents = {}
        self._initialize_agents()
    
    def _initialize_agents(self):
        self.agents = {
            "policy": PolicyAgent(self.data_loader),
            "legal": LegalAgent(self.data_loader),
            "climate": ClimateAgent(self.data_loader),
            "agri_economic": AgriEconomicAgent(self.data_loader),
            "welfare": WelfareAgent(self.data_loader)
        }
    
    def process(self, application_data: Dict[str, Any]) -> AgentResult:
        start_time = np.datetime64("now")
        
        application_data["application_id"] = f"APP-{self.agent_id}-{start_time.astype(str)}"
        
        results = {}
        execution_order = ["policy", "legal", "climate", "agri_economic", "welfare"]
        
        early_stop_reason = None
        
        for agent_key in execution_order:
            agent = self.agents[agent_key]
            
            enriched_data = self._enrich_application_data(application_data, results)
            
            result = agent.process(enriched_data)
            results[agent_key] = result
            
            if self._should_stop_early(agent_key, result):
                early_stop_reason = f"Early stop at {agent.name}: {result.explanation}"
                break
        
        final_recommendation = self._generate_final_recommendation(results)
        
        output = self._compile_output(application_data, results, final_recommendation, start_time, early_stop_reason)
        
        return self.create_result(
            final_recommendation["decision"],
            output,
            final_recommendation["explanation"],
            confidence=final_recommendation["confidence"]
        )
    
    def _enrich_application_data(self, base_data: Dict[str, Any], results: Dict[str, AgentResult]) -> Dict[str, Any]:
        enriched = base_data.copy()
        
        if "policy" in results and results["policy"].status == "ELIGIBLE":
            policy_result = results["policy"].result
            if "recommended_scheme" in policy_result:
                enriched["recommended_scheme"] = policy_result["recommended_scheme"]["scheme_id"]
        
        if "agri_economic" in results and results["agri_economic"].status == "PREDICTED":
            econ_result = results["agri_economic"].result
            enriched["predicted_subsidy"] = econ_result.get("predicted_subsidy_rs", 0)
        
        return enriched
    
    def _should_stop_early(self, agent_key: str, result: AgentResult) -> bool:
        if agent_key == "policy":
            return result.status == "NOT_ELIGIBLE"
        
        if agent_key == "legal":
            return result.status in ["REJECTED", "AREA_MISMATCH"]
        
        if agent_key == "climate":
            return result.status == "NOT_CONFIRMED"
        
        return False
    
    def _generate_final_recommendation(self, results: Dict[str, AgentResult]) -> Dict[str, Any]:
        default_result = AgentResult("", "PENDING", {}, "", np.datetime64("now").astype(str))
        
        policy_status = results.get("policy", default_result).status
        legal_status = results.get("legal", default_result).status
        climate_status = results.get("climate", default_result).status
        welfare_result = results.get("welfare")
        
        decision = "REVIEW"
        explanation = ""
        confidence = 0.5
        
        rejection_reasons = []
        
        if policy_status != "ELIGIBLE":
            rejection_reasons.append("Not eligible under any scheme")
        
        if legal_status == "REJECTED":
            rejection_reasons.append("Land documents rejected")
        elif legal_status == "AREA_MISMATCH":
            rejection_reasons.append("Land area mismatch")
        
        if climate_status == "NOT_CONFIRMED":
            rejection_reasons.append("Disaster not confirmed")
        
        if not rejection_reasons:
            if welfare_result:
                welfare_status = welfare_result.status
                if welfare_result.result.get("priority_level") in ["CRITICAL", "HIGH"]:
                    decision = "RECOMMEND_APPROVE"
                    confidence = 0.90
                elif welfare_status == "REVIEW":
                    decision = "REVIEW"
                    confidence = 0.60
                else:
                    decision = "RECOMMEND_APPROVE"
                    confidence = 0.80
            else:
                decision = "RECOMMEND_APPROVE"
                confidence = 0.75
        
        if rejection_reasons:
            decision = "REJECT"
            explanation = f"Application REJECTED. Reasons: {'; '.join(rejection_reasons)}"
            confidence = 0.95
        elif decision == "RECOMMEND_APPROVE":
            explanation = f"Application eligible for processing. Priority: {welfare_result.result.get('priority_level', 'NORMAL')}. Recommendation: APPROVE"
        else:
            explanation = welfare_result.explanation if welfare_result else "Application requires officer review"
        
        return {
            "decision": decision,
            "explanation": explanation,
            "confidence": confidence,
            "rejection_reasons": rejection_reasons
        }
    
    def _compile_output(
        self, 
        application_data: Dict[str, Any], 
        results: Dict[str, AgentResult],
        final_recommendation: Dict[str, Any],
        start_time: np.datetime64,
        early_stop_reason: str = None
    ) -> Dict[str, Any]:
        execution_time = (np.datetime64("now") - start_time).astype(float) / 1e9
        
        agent_summaries = []
        for key, result in results.items():
            agent_summaries.append({
                "agent": result.agent_name,
                "status": result.status,
                "explanation": result.explanation,
                "confidence": result.confidence
            })
        
        recommended_scheme = None
        predicted_subsidy = None
        priority_level = None
        
        if "policy" in results:
            policy_res = results["policy"].result
            recommended_scheme = policy_res.get("recommended_scheme", {}).get("scheme_name", "N/A")
        
        if "agri_economic" in results:
            econ_res = results["agri_economic"].result
            predicted_subsidy = econ_res.get("predicted_subsidy_rs", 0)
        
        if "welfare" in results:
            welfare_res = results["welfare"].result
            priority_level = welfare_res.get("priority_level", "NORMAL")
        
        return {
            "application_id": application_data.get("application_id"),
            "orchestration_id": self.agent_id,
            "processing_timestamp": np.datetime64("now").astype(str),
            "execution_time_seconds": round(execution_time, 2),
            "early_stop": early_stop_reason is not None,
            "early_stop_reason": early_stop_reason,
            "farmer_info": {
                "name": application_data.get("farmer_name"),
                "aadhar": (application_data.get("aadhar_number", "")[:4] + "XXXX" + application_data.get("aadhar_number", "")[-4:]) if application_data.get("aadhar_number") else "N/A",
                "location": f"{application_data.get('village')}, {application_data.get('district')}, {application_data.get('state')}",
                "farmer_type": application_data.get("farmer_type"),
                "land_area_ha": application_data.get("land_area_hectares")
            },
            "crop_info": {
                "crop": application_data.get("crop"),
                "season": application_data.get("season"),
                "loss_reason": application_data.get("loss_reason"),
                "loss_percentage": application_data.get("loss_percentage")
            },
            "agent_results": agent_summaries,
            "recommended_scheme": recommended_scheme,
            "predicted_subsidy_rs": predicted_subsidy,
            "priority_level": priority_level,
            "final_decision": final_recommendation["decision"],
            "decision_confidence": final_recommendation["confidence"],
            "officer_explanation": final_recommendation["explanation"]
        }
    
    def generate_shap_explanations(self, results: Any) -> Dict[str, Any]:
        shap_explanations = {}
        
        print(f"[DEBUG] Generating SHAP explanations...")
        
        agent_results_dict = {}
        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    agent_name = item.get('agent', '').lower().replace(' ', '_')
                    if 'climate' in agent_name:
                        agent_results_dict['climate'] = item
                    elif 'economic' in agent_name or 'agri' in agent_name:
                        agent_results_dict['agri_economic'] = item
                    elif 'welfare' in agent_name:
                        agent_results_dict['welfare'] = item
        elif isinstance(results, dict):
            agent_results_dict = results
        
        print(f"[DEBUG] Agent results dict: {agent_results_dict.keys()}")
        
        if "climate" in results:
            climate_result = results["climate"]
            if climate_result.status in ["CONFIRMED", "PARTIALLY_CONFIRMED"]:
                try:
                    print(f"[DEBUG] Loading climate model...")
                    climate_model = self.model_loader.load_climate_model()
                    if climate_model:
                        print(f"[DEBUG] Generating climate SHAP...")
                        shap_explanations["climate"] = self._generate_climate_shap(climate_model, climate_result.result)
                    else:
                        shap_explanations["climate_error"] = "Climate model not found"
                except Exception as e:
                    shap_explanations["climate_error"] = str(e)
        
        if "agri_economic" in results:
            econ_result = results["agri_economic"]
            if econ_result.status == "PREDICTED":
                try:
                    print(f"[DEBUG] Loading economic model...")
                    econ_model = self.model_loader.load_economic_model()
                    if econ_model:
                        print(f"[DEBUG] Generating economic SHAP...")
                        shap_explanations["economic"] = self._generate_economic_shap(econ_model, econ_result.result)
                    else:
                        shap_explanations["economic_error"] = "Economic model not found"
                except Exception as e:
                    shap_explanations["economic_error"] = str(e)
        
        if "welfare" in results:
            welfare_result = results["welfare"]
            try:
                print(f"[DEBUG] Loading welfare model...")
                welfare_model = self.model_loader.load_welfare_model()
                if welfare_model:
                    print(f"[DEBUG] Generating welfare SHAP...")
                    shap_explanations["welfare"] = self._generate_welfare_shap(welfare_model, welfare_result.result)
                else:
                    shap_explanations["welfare_error"] = "Welfare model not found"
            except Exception as e:
                shap_explanations["welfare_error"] = str(e)
        
        print(f"[DEBUG] SHAP explanations generated: {shap_explanations.keys()}")
        return shap_explanations
    
    def _generate_climate_shap(self, model, result):
        try:
            if not isinstance(model, RandomForestClassifier):
                return None
            
            feature_names = ["severity_severe", "severity_very_severe", "estimated_loss_pct", "area_hectares"]
            
            severity = result.get("severity", "").lower()
            estimated_loss = result.get("damage_assessment", {}).get("estimated_loss_percentage", 0)
            area = result.get("damage_assessment", {}).get("area_hectares", 0)
            
            input_data = np.array([
                severity == "severe",
                severity == "very_severe",
                estimated_loss / 100,
                area / 100
            ]).reshape(1, -1)
            
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(input_data)
            
            explanation = {}
            for i, name in enumerate(feature_names):
                explanation[name] = float(shap_values[0][i])
            
            return explanation
        except Exception:
            return None
    
    def _generate_economic_shap(self, model, result):
        try:
            feature_names = ["land_area", "loss_percentage", "expected_yield", "msp", "cost_cultivation"]
            
            input_data = np.array([
                result.get("land_area_hectares", 0),
                result.get("loss_percentage", 0) / 100,
                result.get("expected_yield_per_hectare", 0),
                result.get("msp_rs", 0),
                result.get("cost_of_cultivation_rs_ha", 0)
            ]).reshape(1, -1)
            
            if isinstance(model, Ridge):
                explainer = shap.LinearExplainer(model, input_data)
                shap_values = explainer.shap_values(input_data)
                
                explanation = {}
                for i, name in enumerate(feature_names):
                    explanation[name] = float(shap_values[i])
                
                return explanation
            else:
                return None
        except Exception:
            return None
    
    def _generate_welfare_shap(self, model, result):
        try:
            feature_names = ["farmer_type", "land_area", "loss_percentage", "subsidy"]
            
            farmer_type_map = {"small": 1, "marginal": 2, "medium": 3, "large": 4}
            farmer_type_val = farmer_type_map.get(result.get("farmer_type", "small"), 1)
            
            input_data = np.array([
                farmer_type_val,
                result.get("land_area_hectares", 0),
                result.get("loss_percentage", 0) / 100,
                result.get("predicted_subsidy_rs", 0) / 100000
            ]).reshape(1, -1)
            
            if isinstance(model, DecisionTreeClassifier):
                explainer = shap.TreeExplainer(model)
                shap_values = explainer.shap_values(input_data)
                
                explanation = {}
                for i, name in enumerate(feature_names):
                    explanation[name] = float(shap_values[0][i])
                
                return explanation
            else:
                return None
        except Exception:
            return None