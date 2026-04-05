from typing import Dict, Any, Optional
import math

class InsuranceCalculator:
    """
    Crop Insurance Premium Calculator
    Implements PMFBY (Pradhan Mantri Fasal Bima Yojana) calculations
    """
    
    # PMFBY Premium Rates (as per Government guidelines)
    CROP_PREMIUM_RATES = {
        "Kharif": {
            "Cereals": 2.0,      # 2% of sum insured
            "Pulses": 2.0,
            "Oilseeds": 2.0,
            "Vegetables": 5.0,
            "Fruits": 5.0,
            "Cotton": 2.0,
            "Sugarcane": 2.0,
            "Other": 3.0
        },
        "Rabi": {
            "Cereals": 1.5,      # 1.5% of sum insured
            "Pulses": 1.5,
            "Oilseeds": 1.5,
            "Vegetables": 5.0,
            "Fruits": 5.0,
            "Other": 2.0
        },
        "Zaid": {
            "Vegetables": 5.0,
            "Fruits": 5.0,
            "Other": 3.0
        }
    }
    
    # Sum Insured Limits (₹ per hectare)
    CROP_SUM_INSURED = {
        "Paddy": 50000,
        "Wheat": 50000,
        "Maize": 40000,
        "Cotton": 60000,
        "Sugarcane": 75000,
        "Soybean": 40000,
        "Mustard": 35000,
        "Gram": 30000,
        "Tur": 35000,
        "Groundnut": 40000,
        "Vegetables": 50000,
        "Fruits": 75000,
        "Other": 40000
    }
    
    # Claim calculation factors
    AREA_THRESHOLD = {
        "small": 2.0,      # hectares
        "marginal": 1.0   # hectares
    }
    
    def __init__(self):
        pass
    
    def get_crop_category(self, crop: str) -> str:
        """Determine crop category for premium rate"""
        crop_lower = crop.lower()
        
        cereals = ["paddy", "rice", "wheat", "barley", "maize", "jowar", "bajra"]
        pulses = ["gram", "tur", "moong", "masoor", "urad", "rajma", "lentil"]
        oilseeds = ["soybean", "mustard", "groundnut", "sunflower", "sesame", "castor"]
        vegetables = ["tomato", "potato", "onion", "brinjal", "cabbage", "cauliflower", "carrot"]
        fruits = ["mango", "banana", "apple", "orange", "grape", "papaya", "guava"]
        
        if crop_lower in cereals:
            return "Cereals"
        elif crop_lower in pulses:
            return "Pulses"
        elif crop_lower in oilseeds:
            return "Oilseeds"
        elif crop_lower in vegetables:
            return "Vegetables"
        elif crop_lower in fruits:
            return "Fruits"
        elif crop_lower == "cotton":
            return "Cotton"
        elif crop_lower == "sugarcane":
            return "Sugarcane"
        else:
            return "Other"
    
    def get_sum_insured(self, crop: str, land_area: float) -> float:
        """Calculate Sum Insured based on crop and area"""
        base_rate = self.CROP_SUM_INSURED.get(crop, 40000)
        return base_rate * land_area
    
    def calculate_premium(
        self,
        crop: str,
        season: str,
        land_area: float,
        farmer_type: str = "Small",
        loanee: bool = False,
        custom_sum_insured: float = None
    ) -> Dict[str, Any]:
        """
        Calculate crop insurance premium
        
        Args:
            crop: Crop name (e.g., "Paddy", "Cotton")
            season: Season (Kharif, Rabi, Zaid)
            land_area: Land area in hectares
            farmer_type: Small, Marginal, Medium, Large
            loanee: Whether farmer has crop loan
            custom_sum_insured: Optional custom sum insured
        
        Returns:
            Premium calculation details
        """
        # Get crop category and premium rate
        crop_category = self.get_crop_category(crop)
        season_premium_rates = self.CROP_PREMIUM_RATES.get(season, self.CROP_PREMIUM_RATES["Kharif"])
        premium_rate = season_premium_rates.get(crop_category, 2.0)
        
        # Calculate Sum Insured
        if custom_sum_insured:
            sum_insured = custom_sum_insured
        else:
            sum_insured = self.get_sum_insured(crop, land_area)
        
        # Calculate Premium
        premium_amount = (sum_insured * premium_rate) / 100
        
        # Apply farmer type discount
        if farmer_type.lower() in ["small", "marginal"]:
            # Small and Marginal farmers get 50% subsidy from Government
            farmer_share = premium_amount * 0.5
            government_share = premium_amount * 0.5
        else:
            # Other farmers get 45% subsidy
            farmer_share = premium_amount * 0.55
            government_share = premium_amount * 0.45
        
        # Additional loading for loanee farmers (1% extra)
        if loanee:
            loanee_loading = sum_insured * 0.01 / 100
            farmer_share += loanee_loading
            premium_amount += loanee_loading
        
        # Calculate expected claim (based on historical data)
        expected_claim = self._calculate_expected_claim(crop, season, sum_insured)
        
        # Coverage details
        coverage = {
            "sum_insured": round(sum_insured, 2),
            "premium_rate": premium_rate,
            "total_premium": round(premium_amount, 2),
            "farmer_share": round(farmer_share, 2),
            "government_subsidy": round(government_share, 2),
            "area_hectares": land_area,
            "season": season,
            "crop": crop,
            "crop_category": crop_category
        }
        
        return {
            "success": True,
            "coverage": coverage,
            "expected_claim": round(expected_claim, 2),
            "benefits": self._get_benefits_list(crop, season, sum_insured),
            "documents_required": self._get_required_documents(),
            "coverage_type": "Yields/Loass",
            "note": "Premium rates as per PMFBY guidelines. Subject to crop cutting experiments."
        }
    
    def _calculate_expected_claim(self, crop: str, season: str, sum_insured: float) -> float:
        """Calculate expected claim based on historical loss percentage"""
        # Historical loss rates by season
        loss_rates = {
            "Kharif": 0.15,  # 15% average loss
            "Rabi": 0.10,    # 10% average loss
            "Zaid": 0.12     # 12% average loss
        }
        
        loss_rate = loss_rates.get(season, 0.12)
        return sum_insured * loss_rate
    
    def _get_benefits_list(self, crop: str, season: str, sum_insured: float) -> list:
        """Get list of insurance benefits"""
        return [
            f"Coverage up to ₹{sum_insured:,.0f} per hectare",
            "Low premium: Only 2% for Kharif crops",
            "50% subsidy for Small/Marginal farmers",
            "All natural calamities covered",
            "Post-harvest losses covered",
            "Prevented sowing coverage",
            "Localized damage coverage"
        ]
    
    def _get_required_documents(self) -> list:
        """Get list of required documents"""
        return [
            "Land records (Passbook/Title deed)",
            "Aadhar Card",
            "Bank account details",
            "Crop sowing certificate",
            "Mobile number"
        ]
    
    def compare_premiums(
        self,
        crop: str,
        season: str,
        land_area: float
    ) -> Dict[str, Any]:
        """Compare premiums across different sum insured options"""
        
        base_sum_insured = self.get_sum_insured(crop, land_area)
        
        options = [
            {"name": "Standard", "sum_insured": base_sum_insured},
            {"name": "Basic (50%)", "sum_insured": base_sum_insured * 0.5},
            {"name": "Enhanced (150%)", "sum_insured": base_sum_insured * 1.5},
            {"name": "Premium (200%)", "sum_insured": base_sum_insured * 2.0}
        ]
        
        comparison = []
        for opt in options:
            calc = self.calculate_premium(crop, season, land_area, custom_sum_insured=opt["sum_insured"])
            comparison.append({
                "option": opt["name"],
                "sum_insured": opt["sum_insured"],
                "premium": calc["coverage"]["farmer_share"],
                "coverage": calc["coverage"]["sum_insured"]
            })
        
        return {
            "success": True,
            "comparison": comparison,
            "recommendation": "Standard coverage is recommended for most farmers"
        }
    
    def calculate_premium_with_loss_history(
        self,
        crop: str,
        season: str,
        land_area: float,
        loss_history: list  # List of past loss percentages
    ) -> Dict[str, Any]:
        """Calculate premium considering farmer's loss history"""
        
        base_calc = self.calculate_premium(crop, season, land_area)
        
        if not loss_history:
            return base_calc
        
        # Calculate average loss
        avg_loss = sum(loss_history) / len(loss_history)
        
        # Apply no-claim bonus or loading
        if avg_loss < 0.05:
            # No claim bonus - 5% discount
            discount = base_calc["coverage"]["total_premium"] * 0.05
            adjusted_premium = base_calc["coverage"]["total_premium"] - discount
            bonus_note = "No Claim Bonus applied - 5% discount"
        elif avg_loss > 0.20:
            # High loss loading - 10% extra
            loading = base_calc["coverage"]["total_premium"] * 0.10
            adjusted_premium = base_calc["coverage"]["total_premium"] + loading
            bonus_note = "High loss history - 10% loading applied"
        else:
            adjusted_premium = base_calc["coverage"]["total_premium"]
            bonus_note = "Standard premium rate"
        
        base_calc["coverage"]["adjusted_premium"] = round(adjusted_premium, 2)
        base_calc["coverage"]["loss_bonus_note"] = bonus_note
        base_calc["coverage"]["average_loss_history"] = f"{avg_loss*100:.1f}%"
        
        return base_calc


# Singleton instance
_insurance_calculator = None

def get_insurance_calculator() -> InsuranceCalculator:
    global _insurance_calculator
    if _insurance_calculator is None:
        _insurance_calculator = InsuranceCalculator()
    return _insurance_calculator
