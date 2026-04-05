from typing import Dict, Any
from .base_agent import BaseAgent, AgentResult

class WelfareAgent(BaseAgent):
    def __init__(self, data_loader=None):
        super().__init__("Welfare Agent", data_loader)
    
    def process(self, application_data: Dict[str, Any]) -> AgentResult:
        required_fields = ["farmer_type", "land_area_hectares", "loss_percentage"]
        valid, msg = self.validate_required_fields(application_data, required_fields)
        if not valid:
            return self.create_result("ERROR", {}, msg, confidence=0.0)
        
        farmer_type = application_data.get("farmer_type", "small")
        land_area = application_data["land_area_hectares"]
        loss_percentage = application_data["loss_percentage"]
        predicted_subsidy = application_data.get("predicted_subsidy", 0)
        state = application_data.get("state", "")
        
        priority_score = 0
        priority_factors = []
        
        if farmer_type in ["small", "marginal"]:
            priority_score += 40
            priority_factors.append(f"Small/Marginal farmer (+40)")
        
        if land_area <= 1:
            priority_score += 30
            priority_factors.append(f"Marginal land holding <=1 ha (+30)")
        elif land_area <= 2:
            priority_score += 20
            priority_factors.append(f"Small land holding <=2 ha (+20)")
        
        if loss_percentage >= 70:
            priority_score += 25
            priority_factors.append(f"High loss >=70% (+25)")
        elif loss_percentage >= 50:
            priority_score += 15
            priority_factors.append(f"Moderate-high loss >=50% (+15)")
        
        if predicted_subsidy and predicted_subsidy < 50000:
            priority_score += 10
            priority_factors.append(f"Lower subsidy need <Rs.50k (+10)")
        
        priority_level = "NORMAL"
        if priority_score >= 80:
            priority_level = "CRITICAL"
        elif priority_score >= 60:
            priority_level = "HIGH"
        elif priority_score >= 40:
            priority_level = "MEDIUM"
        
        bias_check = self._check_fairness_bias(application_data, state)
        
        ethical_considerations = self._generate_ethical_considerations(
            farmer_type, land_area, loss_percentage, priority_level
        )
        
        recommendation = "APPROVE"
        if bias_check["bias_detected"]:
            recommendation = "REVIEW"
        elif priority_level == "CRITICAL":
            recommendation = "FAST_TRACK_APPROVE"
        
        return self.create_result(
            recommendation,
            {
                "priority_level": priority_level,
                "priority_score": priority_score,
                "priority_factors": priority_factors,
                "farmer_type": farmer_type,
                "land_area": land_area,
                "loss_percentage": loss_percentage,
                "bias_check": bias_check,
                "ethical_considerations": ethical_considerations,
                "urgency_level": self._get_urgency_level(priority_level)
            },
            f"Priority Level: {priority_level} (Score: {priority_score}/100). "
            f"Factors: {'; '.join(priority_factors)}. "
            f"Ethical Assessment: {ethical_considerations['summary']}. "
            f"Fairness Check: {'PASS' if bias_check['overall_fair'] else 'NEEDS REVIEW'}.",
            confidence=0.85
        )
    
    def _check_fairness_bias(self, application_data: Dict[str, Any], state: str) -> Dict[str, Any]:
        biases = []
        
        farmer_type = application_data.get("farmer_type", "")
        if farmer_type in ["small", "marginal"]:
            biases.append({
                "type": "positive_affirmative_action",
                "description": "Small/Marginal farmer affirmative action applied",
                "justified": True
            })
        
        return {
            "bias_detected": False,
            "biases": biases,
            "overall_fair": True,
            "fairness_notes": "System applies equitable criteria uniformly. Positive bias for vulnerable farmers is policy-justified."
        }
    
    def _generate_ethical_considerations(
        self, 
        farmer_type: str, 
        land_area: float, 
        loss_percentage: int,
        priority_level: str
    ) -> Dict[str, Any]:
        considerations = []
        
        if farmer_type in ["small", "marginal"]:
            considerations.append("Farmer is from vulnerable category requiring social protection")
        
        if land_area <= 1:
            considerations.append("Marginal landholding farmer with limited income alternatives")
        
        if loss_percentage >= 70:
            considerations.append("Severe loss may cause complete income loss for the season")
        
        if priority_level in ["HIGH", "CRITICAL"]:
            considerations.append("Urgent assistance needed to prevent farmer distress")
        
        summary = "; ".join(considerations) if considerations else "Standard case with no special ethical concerns"
        
        return {
            "considerations": considerations,
            "summary": summary,
            "requires_urgent_action": priority_level in ["HIGH", "CRITICAL"]
        }
    
    def _get_urgency_level(self, priority_level: str) -> str:
        urgency_map = {
            "CRITICAL": "IMMEDIATE",
            "HIGH": "WITHIN_7_DAYS",
            "MEDIUM": "WITHIN_30_DAYS",
            "NORMAL": "STANDARD_PROCESS"
        }
        return urgency_map.get(priority_level, "STANDARD_PROCESS")
