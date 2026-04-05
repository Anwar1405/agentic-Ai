"""
Agriculture DSS API - Complete Backend with Application Management
"""
import sys
import os
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
from datetime import datetime
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import crewai_setup
from src import storage
from src.utils.data_loader import DataLoader
from src.agents.crewai_orchestrator import CrewAIOrchestrator

app = FastAPI(title="Agriculture DSS API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage.init_db()


def _get_bearer_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return ""
    return auth.split(" ", 1)[1].strip()


def _require_role(request: Request, roles: List[str]) -> Dict[str, str]:
    token = _get_bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization token")
    sess = storage.get_session(token)
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid/expired session")
    if sess.get("role") not in roles:
        raise HTTPException(status_code=403, detail="Insufficient role")
    return sess

# Initialize
data_loader = DataLoader("src/data")
orchestrator = CrewAIOrchestrator(data_loader)

# Application Status: SUBMITTED -> UNDER_AI_REVIEW -> OFFICER_REVIEW -> APPROVED/REJECTED

class FarmerApplication(BaseModel):
    # Scheme Selection
    state: str
    scheme_id: str
    scheme_name: str
    season: str
    year: int
    
    # Farmer Details
    farmer_name: str
    passbook_name: str
    relationship: str
    relative_name: str
    mobile_number: str
    age: int
    caste_category: str
    gender: str
    farmer_type: str
    farmer_category: str
    
    # Residential Details
    residential_state: str
    district: str
    sub_district: str
    village: str
    address: str
    pin_code: str
    
    # Farmer ID
    id_type: str
    id_number: str
    
    # Account Details
    ifsc_available: str
    ifsc_code: str
    bank_state: str
    bank_district: str
    bank_name: str
    bank_branch: str
    account_number: str
    confirm_account: str
    
    # Land & Crop Info
    land_area_hectares: float
    survey_number: str
    patta_number: str
    crop: str
    loss_reason: str
    loss_date: str
    loss_percentage: float
    
    # Financial
    annual_income: Optional[float] = None
    family_size: Optional[int] = None
    requested_amount: Optional[float] = None

@app.get("/")
async def root():
    return {"message": "Agriculture DSS API v2.0", "status": "active", "portals": ["farmer", "officer"]}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "applications_count": len(storage.list_applications())}

# ==================== WEATHER API ====================

@app.get("/api/weather/analyze")
async def analyze_weather(
    district: str = "Pune",
    state: str = "Maharashtra",
    loss_reason: str = "Flood",
    loss_date: str = "2024-07-20"
):
    """Analyze weather data for disaster verification"""
    try:
        from src.utils.weather_service import get_weather_service
        weather_service = get_weather_service()
        result = weather_service.analyze_disaster_risk(district, state, loss_reason, loss_date)
        return {"success": True, "result": result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# ==================== DOCUMENT OCR API ====================

@app.post("/api/ocr/extract")
async def extract_document_info(file: UploadFile = File(...)):
    """Extract information from uploaded document (Aadhar, Voter ID, Land Record)"""
    try:
        # Save uploaded file temporarily
        import tempfile
        import os
        
        suffix = os.path.splitext(file.filename)[1] or '.jpg'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            from src.utils.document_ocr import get_ocr_service
            ocr_service = get_ocr_service()
            result = ocr_service.process_document(image_path=tmp_path)
            return result
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@app.post("/api/ocr/extract-text")
async def extract_text_from_text(text_data: dict):
    """Extract information from text (for pasted document content)"""
    try:
        text = text_data.get("text", "")
        if not text:
            return {"success": False, "error": "No text provided"}
        
        from src.utils.document_ocr import get_ocr_service
        ocr_service = get_ocr_service()
        
        doc_type = ocr_service.detect_document_type(text)
        
        if doc_type == "Aadhar Card":
            extracted = ocr_service.extract_aadhar_info(text)
        elif doc_type == "Voter ID":
            extracted = ocr_service.extract_voter_id_info(text)
        elif doc_type == "Land Record":
            extracted = ocr_service.extract_land_record_info(text)
        else:
            extracted = {"document_type": doc_type}
        
        return {
            "success": True,
            "document_type": doc_type,
            "extracted_data": extracted
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# ==================== GPS VERIFICATION API ====================

class GPSVerificationRequest(BaseModel):
    claimed_lat: float
    claimed_lon: float
    farmer_lat: float
    farmer_lon: float
    land_area_hectares: Optional[float] = None

@app.post("/api/gps/verify-land")
async def verify_land_gps(request: GPSVerificationRequest):
    """Verify if farmer's GPS location matches claimed land location"""
    try:
        from src.utils.gps_verifier import get_gps_verifier
        verifier = get_gps_verifier()
        
        result = verifier.verify_land_location(
            claimed_lat=request.claimed_lat,
            claimed_lon=request.claimed_lon,
            farmer_lat=request.farmer_lat,
            farmer_lon=request.farmer_lon,
            land_area_hectares=request.land_area_hectares
        )
        
        return {"success": True, "result": result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@app.post("/api/gps/estimate-area")
async def estimate_land_area(corners: List[Dict[str, float]]):
    """Estimate land area from GPS coordinates of corners"""
    try:
        from src.utils.gps_verifier import get_gps_verifier
        verifier = get_gps_verifier()
        
        corner_coords = [(c["lat"], c["lon"]) for c in corners]
        area_hectares = verifier.estimate_land_area_from_gps(corner_coords)
        
        return {
            "success": True,
            "estimated_area_hectares": area_hectares,
            "corners_count": len(corners)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@app.post("/api/gps/check-disaster-risk")
async def check_disaster_risk(
    farmer_lat: float,
    farmer_lon: float,
    disaster_lat: float,
    disaster_lon: float,
    disaster_radius_km: float = 50
):
    """Check if location is in disaster-prone area"""
    try:
        from src.utils.gps_verifier import get_gps_verifier
        verifier = get_gps_verifier()
        
        result = verifier.check_location_risk(
            farmer_lat=farmer_lat,
            farmer_lon=farmer_lon,
            disaster_lat=disaster_lat,
            disaster_lon=disaster_lon,
            disaster_radius_km=disaster_radius_km
        )
        
        return {"success": True, "result": result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# ==================== INSURANCE CALCULATOR API ====================

class InsuranceRequest(BaseModel):
    crop: str
    season: str
    land_area: float
    farmer_type: Optional[str] = "Small"
    loanee: Optional[bool] = False
    custom_sum_insured: Optional[float] = None

@app.post("/api/insurance/calculate")
async def calculate_insurance_premium(request: InsuranceRequest):
    """Calculate crop insurance premium"""
    try:
        from src.utils.insurance_calculator import get_insurance_calculator
        calculator = get_insurance_calculator()
        
        result = calculator.calculate_premium(
            crop=request.crop,
            season=request.season,
            land_area=request.land_area,
            farmer_type=request.farmer_type,
            loanee=request.loanee,
            custom_sum_insured=request.custom_sum_insured
        )
        
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@app.post("/api/insurance/compare")
async def compare_insurance_options(
    crop: str,
    season: str,
    land_area: float
):
    """Compare different insurance coverage options"""
    try:
        from src.utils.insurance_calculator import get_insurance_calculator
        calculator = get_insurance_calculator()
        
        result = calculator.compare_premiums(crop, season, land_area)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@app.get("/api/insurance/rates")
async def get_insurance_rates():
    """Get current insurance premium rates"""
    try:
        from src.utils.insurance_calculator import InsuranceCalculator
        calc = InsuranceCalculator()
        
        return {
            "success": True,
            "premium_rates": calc.CROP_PREMIUM_RATES,
            "sum_insured_limits": calc.CROP_SUM_INSURED,
            "note": "Premium rates as per PMFBY guidelines"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==================== FARMER PORTAL API =================###

@app.post("/api/farmer/submit-application")
async def submit_application(application: FarmerApplication):
    try:
        app_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
        app_data = application.dict()
        
        storage.create_application(app_id, app_data)
        try:
            _notify_status_change(app_id, "SUBMITTED")
        except Exception:
            pass
        
        print(f"[API] Application {app_id} submitted")
        
        return {
            "success": True,
            "application_id": app_id,
            "message": "Application submitted successfully! Status: SUBMITTED"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/farmer/track-application/{application_id}")
async def track_application(application_id: str):
    app = storage.get_application(application_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return {
        "success": True,
        "application_id": application_id,
        "status": app["status"],
        "submitted_at": app["submitted_at"],
        "processed_at": app.get("processed_at"),
        "ai_decision": app.get("ai_decision"),
        "officer_decision": app.get("officer_decision")
    }

@app.get("/api/farmer/my-applications")
async def get_farmer_applications(mobile: Optional[str] = None):
    if not mobile:
        return {"success": True, "applications": []}
    apps = storage.list_applications_by_mobile(mobile)
    results = [
        {
            "application_id": a["application_id"],
            "status": a["status"],
            "scheme_name": a["farmer_data"].get("scheme_name"),
            "submitted_at": a["submitted_at"],
        }
        for a in apps
    ]
    return {"success": True, "applications": results}

# ==================== AI PROCESSING ====================

@app.post("/api/ai/process-application/{application_id}")
async def process_with_ai(application_id: str, request: Request):
    _require_role(request, ["officer", "admin"])
    app = storage.get_application(application_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    farmer_data = app["farmer_data"]
    
    storage.set_status(application_id, "UNDER_AI_REVIEW")
    try:
        _notify_status_change(application_id, "UNDER_AI_REVIEW")
    except Exception:
        pass
    
    try:
        # Convert to format for orchestrator
        orchestrator_data = {
            "application_id": application_id,
            "farmer_name": farmer_data.get("farmer_name"),
            "aadhar_number": farmer_data.get("id_number"),
            "state": farmer_data.get("state") or farmer_data.get("residential_state"),
            "district": farmer_data.get("district"),
            "village": farmer_data.get("village"),
            "survey_number": farmer_data.get("survey_number"),
            "patta_number": farmer_data.get("patta_number"),
            "farmer_type": farmer_data.get("farmer_type"),
            "land_area_hectares": farmer_data.get("land_area_hectares"),
            "crop": farmer_data.get("crop"),
            "season": farmer_data.get("season"),
            "scheme_id": farmer_data.get("scheme_id"),
            "loss_reason": farmer_data.get("loss_reason"),
            "loss_date": farmer_data.get("loss_date"),
            "loss_percentage": farmer_data.get("loss_percentage"),
            "annual_income": farmer_data.get("annual_income"),
            "requested_amount": farmer_data.get("requested_amount"),
            "family_size": farmer_data.get("family_size")
        }
        
        # Process through AI agents
        result = orchestrator.process(orchestrator_data)
        
        # Generate SHAP explanations
        shap_explanations = orchestrator.generate_shap_explanations(result.result.get("agent_results", []))
        
        result.result["shap_explanations"] = shap_explanations
        
        ai_payload = {
            "decision": result.result.get("final_decision"),
            "confidence": result.result.get("decision_confidence"),
            "scheme": result.result.get("recommended_scheme"),
            "subsidy": result.result.get("predicted_subsidy_rs"),
            "priority": result.result.get("priority_level"),
            "explanation": result.result.get("officer_explanation"),
            "shap": shap_explanations
        }

        processed_at = datetime.now().isoformat()
        storage.update_application_ai(
            application_id,
            "OFFICER_REVIEW",
            processed_at,
            result.result.get("agent_results", []),
            ai_payload,
        )

        # Auto notification (simulated)
        try:
            _notify_status_change(application_id, "AI_PROCESSING_COMPLETE")
        except Exception:
            pass
        
        return {
            "success": True,
            "application_id": application_id,
            "status": "OFFICER_REVIEW",
            "ai_decision": ai_payload
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        storage.set_status(application_id, "ERROR")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== OFFICER DASHBOARD API ====================

@app.get("/api/officer/applications")
async def get_all_applications(request: Request, status: Optional[str] = None):
    _require_role(request, ["officer", "admin"])
    apps = storage.list_applications(status=status)
    results = []
    for app in apps:
        farmer = app["farmer_data"]
        ai_dec = app.get("ai_decision")
        results.append(
            {
                "application_id": app["application_id"],
                "status": app["status"],
                "farmer_name": farmer.get("farmer_name"),
                "scheme_name": farmer.get("scheme_name"),
                "district": farmer.get("district"),
                "land_area": farmer.get("land_area_hectares"),
                "submitted_at": app["submitted_at"],
                "ai_decision": ai_dec.get("decision") if isinstance(ai_dec, dict) else None,
            }
        )
    return {"success": True, "applications": results, "total": len(results)}

@app.get("/api/officer/application-details/{application_id}")
async def get_application_details(application_id: str, request: Request):
    _require_role(request, ["officer", "admin"])
    app = storage.get_application(application_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return {
        "success": True,
        "application": app
    }

@app.post("/api/officer/update-decision/{application_id}")
async def update_officer_decision(application_id: str, request: Request, decision: str, comment: str = ""):
    _require_role(request, ["officer", "admin"])
    if storage.get_application(application_id) is None:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if decision not in ["APPROVED", "REJECTED", "REVIEW"]:
        raise HTTPException(status_code=400, detail="Invalid decision")
    
    storage.update_application_officer(application_id, decision, comment)

    # Auto notification (simulated)
    try:
        _notify_status_change(application_id, f"OFFICER_{decision}")
    except Exception:
        pass
    
    return {
        "success": True,
        "application_id": application_id,
        "status": decision,
        "message": f"Application {decision}"
    }

# ==================== SCHEMES API ====================

@app.get("/api/schemes")
async def get_schemes():
    try:
        import csv
        csv_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Policy Rule", "agriculture_schemes.csv")
        
        schemes = []
        active_count = 0
        inactive_count = 0
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                status = row.get('status', '').strip().lower()
                is_active = status == 'active'
                
                if is_active:
                    active_count += 1
                else:
                    inactive_count += 1
                
                schemes.append({
                    "scheme_id": row.get('scheme_id', ''),
                    "scheme_name": row.get('scheme_name', ''),
                    "acronym": row.get('acronym', ''),
                    "status": row.get('status', 'Unknown'),
                    "is_active": is_active
                })
        
        return {
            "success": True,
            "schemes": schemes,
            "active_count": active_count,
            "inactive_count": inactive_count,
            "total_count": len(schemes)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "schemes": []
        }

# ==================== REPORTS & ANALYTICS ====================

@app.get("/api/reports/analytics")
async def get_analytics(request: Request):
    _require_role(request, ["officer", "admin"])
    """Get analytics for officer dashboard"""
    apps = storage.list_applications()
    total = len(apps)
    
    by_status = {"SUBMITTED": 0, "UNDER_AI_REVIEW": 0, "OFFICER_REVIEW": 0, "APPROVED": 0, "REJECTED": 0}
    by_scheme = {}
    by_district = {}
    by_district_status: Dict[str, Dict[str, int]] = {}
    by_month = {}
    
    for app in apps:
        status = app.get("status")
        if status in by_status:
            by_status[status] += 1
        
        scheme = app["farmer_data"].get("scheme_name", "Unknown")
        by_scheme[scheme] = by_scheme.get(scheme, 0) + 1
        
        district = app["farmer_data"].get("district", "Unknown")
        by_district[district] = by_district.get(district, 0) + 1

        if district not in by_district_status:
            by_district_status[district] = {"APPROVED": 0, "REJECTED": 0, "PENDING": 0}
        if status == "APPROVED":
            by_district_status[district]["APPROVED"] += 1
        elif status == "REJECTED":
            by_district_status[district]["REJECTED"] += 1
        else:
            by_district_status[district]["PENDING"] += 1
        
        submitted = app.get("submitted_at", "")
        if submitted:
            month = submitted[:7]
            by_month[month] = by_month.get(month, 0) + 1
    
    return {
        "success": True,
        "total_applications": total,
        "by_status": by_status,
        "by_scheme": by_scheme,
        "by_district": by_district,
        "by_district_status": by_district_status,
        "by_month": by_month,
        "approval_rate": round(by_status.get("APPROVED", 0) / total * 100, 1) if total > 0 else 0,
        "rejection_rate": round(by_status.get("REJECTED", 0) / total * 100, 1) if total > 0 else 0
    }

# ==================== NOTIFICATIONS ====================

notifications_db = []

def _notify_status_change(application_id: str, notification_type: str) -> None:
    app = storage.get_application(application_id)
    if app is None:
        return
    farmer = app.get("farmer_data", {})
    mobile = farmer.get("mobile_number", "")
    farmer_name = farmer.get("farmer_name", "")
    message = f"AgriDSS: Dear {farmer_name}, your application {application_id} status: {app.get('status', '')}"
    storage.add_notification(application_id, mobile, notification_type, message)

@app.post("/api/notifications/send")
async def send_notification(application_id: str, notification_type: str):
    """Send notification for status change"""
    if storage.get_application(application_id) is None:
        return {"success": False, "error": "Application not found"}
    app = storage.get_application(application_id)
    farmer = app.get("farmer_data", {}) if app else {}
    mobile = farmer.get("mobile_number", "")
    farmer_name = farmer.get("farmer_name", "")
    message = f"AgriDSS: Dear {farmer_name}, your application {application_id} status: {app.get('status', '') if app else ''}"
    storage.add_notification(application_id, mobile, notification_type, message)
    notifs = storage.get_notifications(application_id)
    return {"success": True, "notification": notifs[-1] if notifs else None}

@app.get("/api/notifications/{application_id}")
async def get_notifications(application_id: str):
    return {"success": True, "notifications": storage.get_notifications(application_id)}

# ==================== APPLICATION HISTORY ====================

@app.get("/api/farmer/application-history/{mobile}")
async def get_application_history(mobile: str):
    """Get all applications for a farmer by mobile number"""
    apps = storage.list_applications_by_mobile(mobile)
    results = []
    for app in apps:
        ai_raw = app.get("ai_decision")
        ai = ai_raw if isinstance(ai_raw, dict) else {}
        results.append(
            {
                "application_id": app["application_id"],
                "status": app["status"],
                "scheme_name": app["farmer_data"].get("scheme_name"),
                "submitted_at": app["submitted_at"],
                "processed_at": app.get("processed_at"),
                "final_decision": app.get("officer_decision") or ai.get("decision"),
            }
        )
    return {"success": True, "applications": results}

# ==================== USER ROLES ====================

@app.post("/api/auth/login")
async def login(email: str, password: str):
    user = storage.verify_user(email, password)
    if user:
        token = storage.create_session(user["email"], user["role"])
        return {"success": True, "user": user, "token": token}
    return {"success": False, "error": "Invalid credentials"}


@app.post("/api/auth/logout")
async def logout(request: Request):
    token = _get_bearer_token(request)
    if token:
        storage.delete_session(token)
    return {"success": True}

@app.get("/api/users")
async def get_users(request: Request):
    _require_role(request, ["admin"])
    return {"success": True, "users": storage.list_users()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
