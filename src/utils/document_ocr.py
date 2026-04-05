import os
import re
from typing import Dict, Any, Optional
import json

class DocumentOCR:
    """
    OCR Service for extracting information from farmer documents
    Uses EasyOCR (free, offline capable) with fallback to regex patterns
    """
    
    def __init__(self):
        self.ocr_reader = None
        self._init_ocr()
    
    def _init_ocr(self):
        """Initialize OCR reader"""
        try:
            import easyocr
            self.ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            print("[OCR] EasyOCR initialized successfully")
        except ImportError:
            print("[OCR] EasyOCR not available, using pattern-based extraction")
        except Exception as e:
            print(f"[OCR] Error initializing EasyOCR: {e}")
    
    def extract_from_image(self, image_path: str) -> Dict[str, Any]:
        """Extract text from image using OCR"""
        if not self.ocr_reader:
            return {"success": False, "error": "OCR not available", "text": ""}
        
        try:
            results = self.ocr_reader.readtext(image_path)
            text = " ".join([result[1] for result in results])
            return {
                "success": True,
                "text": text,
                "raw_results": results
            }
        except Exception as e:
            return {"success": False, "error": str(e), "text": ""}
    
    def extract_aadhar_info(self, text: str) -> Dict[str, Any]:
        """Extract information from Aadhar card text"""
        result = {
            "document_type": "Aadhar",
            "aadhar_number": None,
            "name": None,
            "dob": None,
            "gender": None,
            "address": None,
            "year_of_birth": None
        }
        
        # Extract Aadhar number (12 digits, with spaces)
        aadhar_pattern = r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'
        aadhar_match = re.search(aadhar_pattern, text)
        if aadhar_match:
            aadhar_num = re.sub(r'[\s-]', '', aadhar_match.group())
            if len(aadhar_num) == 12:
                result["aadhar_number"] = aadhar_num
        
        # Extract year of birth
        dob_patterns = [
            r'DOB[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})',
            r'Year of Birth[:\s]*(\d{4})',
            r'(\d{2}[/-]\d{2}[/-]\d{4})',
            r'\b(19\d{2}|20[0-2]\d)\b'
        ]
        for pattern in dob_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                year_str = match.group(1)
                if len(year_str) == 4:
                    result["year_of_birth"] = int(year_str)
                elif re.match(r'\d{2}[/-]\d{2}[/-]\d{4}', year_str):
                    result["dob"] = year_str
                    result["year_of_birth"] = int(year_str[-4:])
                break
        
        # Extract gender
        if re.search(r'\bMale\b', text, re.IGNORECASE):
            result["gender"] = "Male"
        elif re.search(r'\bFemale\b', text, re.IGNORECASE):
            result["gender"] = "Female"
        
        # Extract name (usually first line after "Aadhar" or "UIDAI")
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'aadhar' in line.lower() or 'uidai' in line.lower():
                if i + 1 < len(lines):
                    name_line = lines[i + 1].strip()
                    if name_line and len(name_line) > 2:
                        result["name"] = name_line
                        break
        
        # Extract address (lines with pincode)
        pincode_pattern = r'\b\d{6}\b'
        for line in lines:
            if re.search(pincode_pattern, line):
                result["address"] = line.strip()
                break
        
        return result
    
    def extract_voter_id_info(self, text: str) -> Dict[str, Any]:
        """Extract information from Voter ID text"""
        result = {
            "document_type": "Voter ID",
            "voter_id": None,
            "name": None,
            "relative_name": None,
            "age": None,
            "gender": None,
            "address": None
        }
        
        # Extract Voter ID (various patterns)
        voter_patterns = [
            r'EPIC\s*[:\-]?\s*([A-Z\d]+)',
            r'Voter\s*ID\s*[:\-]?\s*([A-Z\d]+)',
            r'[A-Z]{3}\d{7}',
        ]
        for pattern in voter_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["voter_id"] = match.group(0)
                break
        
        # Extract name
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'name' in line.lower() and i + 1 < len(lines):
                name = lines[i + 1].strip()
                if name and len(name) > 2:
                    result["name"] = name
                    break
        
        # Extract age
        age_pattern = r'Age[:\s]*(\d{1,3})'
        match = re.search(age_pattern, text, re.IGNORECASE)
        if match:
            result["age"] = int(match.group(1))
        
        # Extract gender
        if re.search(r'\bMale\b', text, re.IGNORECASE):
            result["gender"] = "Male"
        elif re.search(r'\bFemale\b', text, re.IGNORECASE):
            result["gender"] = "Female"
        
        return result
    
    def extract_land_record_info(self, text: str) -> Dict[str, Any]:
        """Extract information from land record document"""
        result = {
            "document_type": "Land Record",
            "survey_number": None,
            "patta_number": None,
            "land_owner": None,
            "area_hectares": None,
            "village": None,
            "district": None
        }
        
        # Extract survey number
        survey_patterns = [
            r'Survey\s*No[:\s]*([A-Z\d/\-]+)',
            r'Survey\s*Number[:\s]*([A-Z\d/\-]+)',
            r'S\.No[:\s.]*([A-Z\d/\-]+)',
        ]
        for pattern in survey_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["survey_number"] = match.group(1)
                break
        
        # Extract patta number
        patta_patterns = [
            r'Patta\s*No[:\s]*([A-Z\d/\-]+)',
            r'Patta\s*Number[:\s]*([A-Z\d/\-]+)',
        ]
        for pattern in patta_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["patta_number"] = match.group(1)
                break
        
        # Extract area
        area_patterns = [
            r'(\d+\.?\d*)\s*(hectares?|ha)',
            r'Area[:\s]*(\d+\.?\d*)\s*(hectares?|ha)?',
        ]
        for pattern in area_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                area = float(match.group(1))
                unit = match.group(2).lower() if match.lastindex and match.lastindex >= 2 else "ha"
                if unit and 'acre' in unit:
                    area = area * 0.404686  # Convert acres to hectares
                result["area_hectares"] = round(area, 4)
                break
        
        # Extract village
        village_pattern = r'Village[:\s]*([A-Za-z\s]+)'
        match = re.search(village_pattern, text, re.IGNORECASE)
        if match:
            result["village"] = match.group(1).strip()
        
        # Extract district
        district_pattern = r'District[:\s]*([A-Za-z\s]+)'
        match = re.search(district_pattern, text, re.IGNORECASE)
        if match:
            result["district"] = match.group(1).strip()
        
        # Extract owner name
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'owner' in line.lower() and i + 1 < len(lines):
                owner = lines[i + 1].strip()
                if owner and len(owner) > 2:
                    result["land_owner"] = owner
                    break
        
        return result
    
    def detect_document_type(self, text: str) -> str:
        """Detect the type of document from text"""
        text_lower = text.lower()
        
        if 'aadhar' in text_lower or 'uidai' in text_lower or re.search(r'\d{4}[\s-]?\d{4}[\s-]?\d{4}', text):
            return "Aadhar Card"
        elif 'voter' in text_lower or 'epic' in text_lower:
            return "Voter ID"
        elif 'land' in text_lower or 'survey' in text_lower or 'patta' in text_lower or 'khata' in text_lower:
            return "Land Record"
        elif 'bank' in text_lower or 'account' in text_lower or 'ifsc' in text_lower:
            return "Bank Document"
        elif 'ration' in text_lower:
            return "Ration Card"
        else:
            return "Unknown"
    
    def process_document(self, image_path: str = None, text: str = None) -> Dict[str, Any]:
        """Process document and extract information"""
        if not text and not image_path:
            return {"success": False, "error": "No input provided"}
        
        # Get text from image if provided
        if image_path and not text:
            ocr_result = self.extract_from_image(image_path)
            if not ocr_result["success"]:
                return ocr_result
            text = ocr_result["text"]
        
        if not text:
            return {"success": False, "error": "Could not extract text"}
        
        # Detect document type
        doc_type = self.detect_document_type(text)
        
        # Extract relevant information based on type
        if doc_type == "Aadhar Card":
            extracted = self.extract_aadhar_info(text)
        elif doc_type == "Voter ID":
            extracted = self.extract_voter_id_info(text)
        elif doc_type == "Land Record":
            extracted = self.extract_land_record_info(text)
        else:
            extracted = {"document_type": doc_type}
        
        return {
            "success": True,
            "document_type": doc_type,
            "extracted_data": extracted,
            "raw_text": text[:500]  # First 500 chars
        }


# Singleton instance
_ocr_service = None

def get_ocr_service() -> DocumentOCR:
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = DocumentOCR()
    return _ocr_service
