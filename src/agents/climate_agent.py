from typing import Dict, Any
from datetime import datetime
from .base_agent import BaseAgent, AgentResult

class ClimateAgent(BaseAgent):
    def __init__(self, data_loader=None):
        super().__init__("Climate Agent", data_loader)
        self.use_weather_api = True
    
    def process(self, application_data: Dict[str, Any]) -> AgentResult:
        required_fields = ["state", "district", "loss_reason", "loss_date"]
        valid, msg = self.validate_required_fields(application_data, required_fields)
        if not valid:
            return self.create_result("ERROR", {}, msg, confidence=0.0)
        
        state = application_data["state"]
        district = application_data["district"]
        loss_reason = application_data["loss_reason"]
        loss_date = application_data["loss_date"]
        
        # First check local disaster database
        disaster_event = self.data_loader.get_disaster_by_location(state, district, loss_reason)
        
        # Try weather API verification if local data not found or as additional verification
        weather_result = None
        if self.use_weather_api:
            try:
                from ..utils.weather_service import get_weather_service
                weather_service = get_weather_service()
                weather_result = weather_service.analyze_disaster_risk(district, state, loss_reason, loss_date)
            except Exception as e:
                print(f"[ClimateAgent] Weather API error: {e}")
        
        # If no local disaster data, use weather API
        if disaster_event is None:
            # Check weather API for verification
            if weather_result and weather_result.get("weather_verified"):
                risk_factors = weather_result.get("risk_factors", [])
                confidence = weather_result.get("confidence_score", 0.5)
                
                return self.create_result(
                    "WEATHER_VERIFIED",
                    {
                        "disaster_confirmed": True,
                        "disaster_type_reported": loss_reason,
                        "verification_method": "weather_api",
                        "weather_data": weather_result.get("weather_data"),
                        "risk_factors": risk_factors,
                        "location": f"{district}, {state}"
                    },
                    f"Weather data VERIFIED: {loss_reason} in {district}, {state}. " + "; ".join(risk_factors),
                    confidence=min(confidence, 0.85)
                )
            
            # Check for alternative disaster in local data
            alternative_disaster = self.data_loader.get_disaster_by_location(state, district)
            
            if alternative_disaster:
                note = "No disaster of reported type found in local records"
                if weather_result:
                    note += f". Weather API: {weather_result.get('explanation', '')}"
                    
                return self.create_result(
                    "NOT_CONFIRMED",
                    {
                        "disaster_confirmed": False,
                        "disaster_type_reported": loss_reason,
                        "disaster_type_actual": alternative_disaster.get("disaster_type"),
                        "note": note,
                        "weather_verification": weather_result if weather_result else None
                    },
                    f"Reported disaster '{loss_reason}' NOT confirmed for {district}, {state}. However, {alternative_disaster['disaster_type']} was recorded in {alternative_disaster['start_date']} to {alternative_disaster.get('end_date', 'ongoing')}." +
                    (f" Weather API: {weather_result.get('explanation', '')}" if weather_result else ""),
                    confidence=0.4
                )
            
            # No disaster data at all - use weather API result
            if weather_result:
                return self.create_result(
                    "WEATHER_ANALYSIS",
                    {
                        "disaster_confirmed": weather_result.get("weather_verified", False),
                        "disaster_type_reported": loss_reason,
                        "location": f"{district}, {state}",
                        "weather_data": weather_result.get("weather_data"),
                        "risk_factors": weather_result.get("risk_factors", []),
                        "explanation": weather_result.get("explanation", "")
                    },
                    f"Weather analysis for {district}, {state}: {weather_result.get('explanation', 'No data available')}",
                    confidence=weather_result.get("confidence_score", 0.3)
                )
            
            return self.create_result(
                "NOT_CONFIRMED",
                {
                    "disaster_confirmed": False,
                    "disaster_type_reported": loss_reason,
                    "location": f"{district}, {state}"
                },
                f"No disaster event recorded for {district}, {state}. Cannot confirm {loss_reason} occurrence.",
                confidence=0.3
            )
        
        # Local disaster event found - enhance with weather API data
        event_severity = disaster_event.get("severity", "unknown")
        event_start = disaster_event.get("start_date", "")
        event_end = disaster_event.get("end_date", "ongoing")
        
        severity_score = {
            "low": 0.3,
            "moderate": 0.6,
            "severe": 0.85,
            "very_severe": 0.95
        }.get(event_severity, 0.5)
        
        # Adjust confidence with weather data if available
        if weather_result and weather_result.get("weather_verified"):
            weather_confidence = weather_result.get("confidence_score", 0.5)
            severity_score = (severity_score + weather_confidence) / 2
        
        affected_crops = disaster_event.get("damage_assessment", {}).get("crops_affected", [])
        reported_crop = application_data.get("crop", "").lower()
        
        crop_affected = any(
            reported_crop == crop.lower() or 
            crop.lower() in reported_crop or 
            reported_crop in crop.lower()
            for crop in affected_crops
        )
        
        additional_info = ""
        if weather_result:
            additional_info = f" | Weather verification: {', '.join(weather_result.get('risk_factors', []))}"
        
        if not crop_affected and affected_crops:
            explanation = (
                f"Disaster {disaster_event['disaster_type'].upper()} CONFIRMED in {district} from {event_start} to {event_end}. "
                f"Severity: {event_severity.upper()}. However, the reported crop '{application_data.get('crop')}' was not in the "
                f"officially affected crops list: {', '.join(affected_crops)}.{additional_info}"
            )
            return self.create_result(
                "PARTIALLY_CONFIRMED",
                {
                    "disaster_confirmed": True,
                    "disaster_type": disaster_event["disaster_type"],
                    "severity": event_severity,
                    "event_id": disaster_event["event_id"],
                    "start_date": event_start,
                    "end_date": event_end,
                    "affected_crops": affected_crops,
                    "reported_crop_affected": False,
                    "damage_assessment": disaster_event.get("damage_assessment", {}),
                    "weather_verification": weather_result if weather_result else None
                },
                explanation,
                confidence=severity_score * 0.7
            )
        
        return self.create_result(
            "CONFIRMED",
            {
                "disaster_confirmed": True,
                "disaster_type": disaster_event["disaster_type"],
                "severity": event_severity,
                "event_id": disaster_event["event_id"],
                "start_date": event_start,
                "end_date": event_end,
                "affected_crops": affected_crops,
                "reported_crop_affected": True,
                "damage_assessment": disaster_event.get("damage_assessment", {}),
                "weather_verification": weather_result if weather_result else None
            },
            f"Disaster {disaster_event['disaster_type'].upper()} CONFIRMED in {district}, {state} from {event_start} to {event_end}. "
            f"Severity: {event_severity.upper()}. Estimated crop loss: {disaster_event.get('damage_assessment', {}).get('estimated_loss_percentage', 'N/A')}%.{additional_info}",
            confidence=severity_score
        )
