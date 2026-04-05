from typing import Dict, Any
import csv
import os
from .base_agent import BaseAgent, AgentResult

class PolicyAgent(BaseAgent):
    def __init__(self, data_loader=None):
        super().__init__("Policy Agent", data_loader)
        self.schemes_data = self._load_schemes_from_csv()
        print(f"[DEBUG] PolicyAgent loaded {len(self.schemes_data)} schemes from CSV")
    
    def _load_schemes_from_csv(self):
        csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Policy Rule", "agriculture_schemes.csv")
        schemes = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    schemes.append({
                        "scheme_id": row.get('scheme_id', ''),
                        "scheme_name": row.get('scheme_name', ''),
                        "acronym": row.get('acronym', ''),
                        "status": row.get('status', 'Unknown'),
                        "eligibility_criteria": row.get('eligibility_criteria', ''),
                        "landholding_criteria": row.get('landholding_criteria', ''),
                        "benefits_provided": row.get('benefits_provided', ''),
                        "scheme_category": row.get('scheme_category', ''),
                        "target_beneficiaries": row.get('target_beneficiaries', '')
                    })
            print(f"[DEBUG] Loaded {len(schemes)} schemes from CSV")
        except Exception as e:
            print(f"Error loading CSV: {e}")
        
        return schemes
    
    def process(self, application_data: Dict[str, Any]) -> AgentResult:
        print(f"[DEBUG] PolicyAgent processing: {application_data}")
        
        required_fields = ["state", "district", "crop", "season", "farmer_type", "land_area_hectares"]
        valid, msg = self.validate_required_fields(application_data, required_fields)
        if not valid:
            return self.create_result("ERROR", {}, msg, confidence=0.0)
        
        state = application_data.get("state", "")
        crop = application_data.get("crop", "").lower()
        season = application_data.get("season", "").lower()
        farmer_type = application_data.get("farmer_type", "").lower()
        land_area = float(application_data.get("land_area_hectares", 0))
        loss_percentage = float(application_data.get("loss_percentage", 0))
        selected_scheme_id = application_data.get("scheme_id", "")
        
        print(f"[DEBUG] Farmer type: {farmer_type}, Land: {land_area}, Loss: {loss_percentage}%")
        
        active_schemes = [s for s in self.schemes_data if s["status"].lower() == "active"]
        print(f"[DEBUG] Active schemes: {len(active_schemes)}")
        
        if not active_schemes:
            return self.create_result(
                "NOT_ELIGIBLE",
                {"eligible_schemes": [], "reasons": ["No active schemes available"]},
                "No active schemes found in the system.",
                confidence=0.95
            )
        
        eligible_schemes = []
        ineligible_reasons = []
        
        for scheme in active_schemes:
            scheme_id = scheme["scheme_id"]
            
            is_eligible = True
            reasons = []
            
            if not farmer_type or farmer_type == "":
                is_eligible = False
                reasons.append("Farmer type is required")
            
            if loss_percentage < 20:
                is_eligible = False
                reasons.append(f"Loss {loss_percentage}% below minimum 20%")
            
            if land_area <= 0:
                is_eligible = False
                reasons.append("Land area must be greater than 0")
            
            if is_eligible:
                eligible_schemes.append({
                    "scheme_id": scheme_id,
                    "scheme_name": scheme["scheme_name"],
                    "description": scheme.get("benefits_provided", "")[:100]
                })
        
        print(f"[DEBUG] Eligible schemes: {len(eligible_schemes)}")
        
        if not eligible_schemes:
            return self.create_result(
                "NOT_ELIGIBLE",
                {"eligible_schemes": [], "reasons": ineligible_reasons, "debug": {
                    "farmer_type": farmer_type,
                    "land_area": land_area,
                    "loss_percentage": loss_percentage
                }},
                f"Not eligible. Loss {loss_percentage}% must be 20%+ and valid farmer type required.",
                confidence=0.90
            )
        
        recommended = eligible_schemes[0]
        
        return self.create_result(
            "ELIGIBLE",
            {
                "eligible_schemes": eligible_schemes,
                "recommended_scheme": recommended,
                "farmer_type": farmer_type,
                "land_area": land_area,
                "loss_percentage": loss_percentage
            },
            f"Farmer eligible for {len(eligible_schemes)} scheme(s). Recommended: {recommended['scheme_name']}",
            confidence=0.90
        )
