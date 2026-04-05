import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.data_loader import DataLoader
from src.agents.crewai_orchestrator import CrewAIOrchestrator
import json
from typing import Dict, Any

def load_data():
    data_dir = "src/data"
    return DataLoader(data_dir)

def process_application(application_data: Dict[str, Any], data_loader) -> Dict[str, Any]:
    crewai_orchestrator = CrewAIOrchestrator(data_loader)
    result = crewai_orchestrator.process(application_data)
    
    shap_explanations = crewai_orchestrator.generate_shap_explanations(
        result.result.get("agent_results", [])
    )
    
    result.result["shap_explanations"] = shap_explanations
    
    return result.to_dict()

def print_report(output: Dict[str, Any]):
    output_data = output.get('result', output)
    
    shap_explanations = output_data.get('shap_explanations', {})
    
    print("\n" + "="*80)
    print("AGRICULTURE DEPARTMENT - CROP LOSS SUBSIDY DECISION SUPPORT SYSTEM")
    print("="*80)
    print(f"\nApplication ID: {output_data.get('application_id', 'N/A')}")
    print(f"Processing Time: {output_data.get('execution_time_seconds', 0):.2f} seconds")
    print(f"Processed at: {output_data.get('processing_timestamp', '')}")
    
    farmer = output_data.get('farmer_info', {})
    print("\n" + "-"*40)
    print("FARMER INFORMATION")
    print("-"*40)
    print(f"Name: {farmer.get('name', 'N/A')}")
    print(f"Aadhar: {farmer.get('aadhar', 'N/A')}")
    print(f"Location: {farmer.get('location', 'N/A')}")
    print(f"Farmer Type: {farmer.get('farmer_type', 'N/A')}")
    print(f"Land Area: {farmer.get('land_area_ha', 'N/A')} ha")
    
    crop = output_data.get('crop_info', {})
    print("\n" + "-"*40)
    print("CROP & LOSS DETAILS")
    print("-"*40)
    print(f"Crop: {crop.get('crop', 'N/A')}")
    print(f"Season: {crop.get('season', 'N/A')}")
    print(f"Loss Reason: {crop.get('loss_reason', 'N/A')}")
    print(f"Loss Percentage: {crop.get('loss_percentage', 'N/A')}%")
    
    print("\n" + "-"*40)
    print("AGENT ANALYSIS RESULTS")
    print("-"*40)
    for agent_result in output_data.get('agent_results', []):
        status_emoji = {
            "ELIGIBLE": "[OK]",
            "NOT_ELIGIBLE": "[X]",
            "VERIFIED": "[OK]",
            "NOT_VERIFIED": "[?]",
            "PENDING": "[P]",
            "REJECTED": "[X]",
            "CONFIRMED": "[OK]",
            "NOT_CONFIRMED": "[X]",
            "PARTIALLY_CONFIRMED": "[~]",
            "PREDICTED": "[OK]",
            "APPROVE": "[OK]",
            "FAST_TRACK_APPROVE": "[!!]",
            "REVIEW": "[?]",
            "MISMATCH": "[X]"
        }.get(agent_result.get('status', ''), "[ ]")
        
        print(f"\n{status_emoji} {agent_result.get('agent', 'Unknown')}: {agent_result.get('status', 'N/A')}")
        print(f"   Explanation: {agent_result.get('explanation', 'N/A')}")
        print(f"   Confidence: {agent_result.get('confidence', 0)*100:.0f}%")
    
    if shap_explanations:
        print("\n" + "-"*40)
        print("SHAP EXPLANATIONS")
        print("-"*40)
        
        for agent_type, explanation in shap_explanations.items():
            if agent_type.endswith("_error"):
                continue
            
            print(f"\nSHAP for {agent_type.upper()}")
            if not explanation:
                print("   No explanation available")
                continue
            
            top_features = sorted(explanation.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
            print("   Top 5 Influencing Factors:")
            for feature, value in top_features:
                impact = "+" if value >= 0 else ""
                print(f"   {feature}: {impact}{value:.2f}")
    
    print("\n" + "="*80)
    print("FINAL RECOMMENDATION FOR OFFICER")
    print("="*80)
    
    decision = output_data.get('final_decision', 'UNKNOWN')
    decision_display = {
        "RECOMMEND_APPROVE": ">>> RECOMMEND APPROVE <<<",
        "REJECT": ">>> REJECT <<<",
        "REVIEW": ">>> REVIEW REQUIRED <<<"
    }.get(decision, decision)
    
    print(f"\nDecision: {decision_display}")
    print(f"Confidence: {output_data.get('decision_confidence', 0)*100:.0f}%")
    print(f"\nRecommended Scheme: {output_data.get('recommended_scheme', 'N/A')}")
    print(f"Predicted Subsidy Amount: Rs.{output_data.get('predicted_subsidy_rs', 0):,.2f}")
    print(f"Priority Level: {output_data.get('priority_level', 'N/A')}")
    print(f"\nOfficer Explanation:")
    print(f"   {output_data.get('officer_explanation', 'N/A')}")
    
    if output_data.get('early_stop'):
        print(f"\n[Note: Processing stopped early - {output_data.get('early_stop_reason', 'N/A')}]")
    
    print("\n" + "="*80)
    print("END OF REPORT")
    print("="*80 + "\n")

def get_sample_application() -> Dict[str, Any]:
    return {
        "farmer_name": "Ramesh Narayan Patil",
        "aadhar_number": "987654321012",
        "state": "Maharashtra",
        "district": "Pune",
        "village": "Velhe",
        "survey_number": "123/1A",
        "patta_number": "PT/2020/12345",
        "farmer_type": "small",
        "land_area_hectares": 2.5,
        "crop": "paddy",
        "season": "kharif",
        "loss_reason": "flood",
        "loss_date": "2024-07-20",
        "loss_percentage": 65
    }

def run_cli():
    print("\n" + "="*60)
    print("AGRICULTURE DSS - Agentic AI System")
    print("="*60)
    
    data_loader = load_data()
    print("Data loaded successfully.")
    
    print("\nProcessing sample application...")
    
    application = get_sample_application()
    
    print(f"\nFarmer: {application['farmer_name']}")
    print(f"Location: {application['village']}, {application['district']}, {application['state']}")
    print(f"Crop: {application['crop']}, Season: {application['season']}")
    print(f"Loss: {application['loss_reason']} - {application['loss_percentage']}%")
    
    result = process_application(application, data_loader)
    
    print_report(result)
    
    return result

if __name__ == "__main__":
    run_cli()
