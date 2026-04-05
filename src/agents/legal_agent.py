from typing import Dict, Any
from .base_agent import BaseAgent, AgentResult

class LegalAgent(BaseAgent):
    def __init__(self, data_loader=None):
        super().__init__("Legal Agent", data_loader)
    
    def process(self, application_data: Dict[str, Any]) -> AgentResult:
        required_fields = ["aadhar_number", "survey_number", "village", "state"]
        valid, msg = self.validate_required_fields(application_data, required_fields)
        if not valid:
            return self.create_result("ERROR", {}, msg, confidence=0.0)
        
        aadhar = application_data["aadhar_number"]
        survey_number = application_data["survey_number"]
        village = application_data.get("village", "")
        applicant_name = application_data.get("farmer_name", "")
        
        land_record = self.data_loader.get_land_record(survey_number=survey_number, aadhar=aadhar)
        
        if land_record is None:
            return self.create_result(
                "NOT_VERIFIED",
                {
                    "land_record_found": False,
                    "survey_number": survey_number,
                    "aadhar_number": aadhar
                },
                f"No land record found for survey number {survey_number}. Document verification pending.",
                confidence=0.5
            )
        
        verification_status = land_record.get("verification_status", "unknown")
        
        if verification_status == "rejected":
            return self.create_result(
                "REJECTED",
                {
                    "land_record_found": True,
                    "verification_status": "rejected",
                    "land_record": land_record
                },
                f"Land record verification REJECTED. Survey number {survey_number} is invalid or fraudulent.",
                confidence=0.95
            )
        
        if verification_status == "pending_verification":
            return self.create_result(
                "PENDING",
                {
                    "land_record_found": True,
                    "verification_status": "pending",
                    "land_record": land_record
                },
                f"Land record verification PENDING. Awaiting physical verification at Talathi office.",
                confidence=0.7
            )
        
        name_match = False
        if applicant_name:
            record_name = land_record.get("owner_name", "").lower()
            applicant_name_lower = applicant_name.lower()
            
            # More flexible name matching
            applicant_parts = set(applicant_name_lower.split())
            record_parts = set(record_name.split())
            
            # Check if at least one name part matches
            common_parts = applicant_parts & record_parts
            name_match = len(common_parts) >= 1 or (
                record_name == applicant_name_lower or
                applicant_name_lower in record_name or
                record_name in applicant_name_lower or
                record_name.split()[-1] == applicant_name_lower.split()[-1]
            )
        
        if not name_match and applicant_name:
            return self.create_result(
                "MISMATCH",
                {
                    "land_record_found": True,
                    "verification_status": "verified",
                    "name_mismatch": True,
                    "land_record": land_record,
                    "applicant_name": applicant_name,
                    "record_name": land_record.get("owner_name")
                },
                f"Name mismatch: Applicant '{applicant_name}' does not match land record owner '{land_record.get('owner_name')}'.",
                confidence=0.85
            )
        
        area_match = True
        declared_area = application_data.get("land_area_hectares")
        record_area = land_record.get("land_area_hectares")
        
        if declared_area and record_area:
            area_diff_percent = abs(declared_area - record_area) / record_area * 100
            if area_diff_percent > 20:
                area_match = False
                return self.create_result(
                    "AREA_MISMATCH",
                    {
                        "land_record_found": True,
                        "verification_status": "verified",
                        "declared_area": declared_area,
                        "record_area": record_area,
                        "difference_percent": area_diff_percent
                    },
                    f"Land area mismatch: Declared {declared_area} ha vs record {record_area} ha (diff: {area_diff_percent:.1f}%)",
                    confidence=0.90
                )
        
        return self.create_result(
            "VERIFIED",
            {
                "land_record_found": True,
                "verification_status": "verified",
                "land_record": {
                    "survey_number": land_record.get("survey_number"),
                    "patta_number": land_record.get("patta_number"),
                    "owner_name": land_record.get("owner_name"),
                    "village": land_record.get("village"),
                    "district": land_record.get("district"),
                    "state": land_record.get("state"),
                    "area_hectares": record_area,
                    "verified_by": land_record.get("verified_by"),
                    "verification_date": land_record.get("verification_date")
                },
                "name_verified": name_match or not applicant_name,
                "area_verified": True
            },
            f"Land ownership and documents VERIFIED. Survey number: {survey_number}, Patta: {land_record.get('patta_number')}, Area: {record_area} ha",
            confidence=0.92
        )
