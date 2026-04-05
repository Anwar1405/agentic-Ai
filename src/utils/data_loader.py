import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

class DataLoader:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path(__file__).parent / "data"
        self.data_dir = Path(data_dir)
        self._cache: Dict[str, Any] = {}
    
    def load_json(self, filename: str) -> Dict[str, Any]:
        if filename in self._cache:
            return self._cache[filename]
        
        file_path = self.data_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self._cache[filename] = data
        return data
    
    @property
    def policy_schemes(self) -> Dict[str, Any]:
        return self.load_json("policy_schemes.json")
    
    @property
    def climate_disasters(self) -> Dict[str, Any]:
        return self.load_json("climate_disasters.json")
    
    @property
    def crop_statistics(self) -> Dict[str, Any]:
        return self.load_json("crop_statistics.json")
    
    @property
    def land_verification(self) -> Dict[str, Any]:
        return self.load_json("land_verification.json")
    
    @property
    def budget(self) -> Dict[str, Any]:
        return self.load_json("budget.json")
    
    def get_crop_by_name(self, crop_name: str) -> Optional[Dict[str, Any]]:
        crops = self.crop_statistics["crops"]
        for crop in crops:
            if crop["crop_name"].lower() == crop_name.lower() or crop["crop_id"].lower() == crop_name.lower():
                return crop
        return None
    
    def get_disaster_by_location(self, state: str, district: str, disaster_type: str = None) -> Optional[Dict[str, Any]]:
        events = self.climate_disasters["disaster_events"]
        for event in events:
            if event["state"].lower() == state.lower() and event["district"].lower() == district.lower():
                if disaster_type is None or event["disaster_type"].lower() == disaster_type.lower():
                    return event
        return None
    
    def get_land_record(self, survey_number: str = None, aadhar: str = None) -> Optional[Dict[str, Any]]:
        records = self.land_verification["land_records"]
        for record in records:
            if survey_number and record.get("survey_number") == survey_number:
                return record
            if aadhar and record.get("aadhar_number") == aadhar:
                return record
        return None
    
    def get_scheme_by_id(self, scheme_id: str) -> Optional[Dict[str, Any]]:
        schemes = self.policy_schemes["schemes"]
        for scheme in schemes:
            if scheme["scheme_id"] == scheme_id:
                return scheme
        return None
    
    def get_budget_for_scheme(self, state: str, scheme_id: str) -> Optional[Dict[str, Any]]:
        allocations = self.budget["budget_allocation"]
        for allocation in allocations:
            if allocation["state"].lower() == state.lower() and allocation["scheme"] == scheme_id:
                return allocation
        return None
