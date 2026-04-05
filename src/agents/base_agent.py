from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid

@dataclass
class AgentResult:
    agent_name: str
    status: str
    result: Dict[str, Any]
    explanation: str
    timestamp: str
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "result": self.result,
            "explanation": self.explanation,
            "timestamp": self.timestamp,
            "confidence": self.confidence
        }

class BaseAgent(ABC):
    def __init__(self, name: str, data_loader=None):
        self.name = name
        self.data_loader = data_loader
        self.agent_id = str(uuid.uuid4())[:8]
    
    @abstractmethod
    def process(self, application_data: Dict[str, Any]) -> AgentResult:
        pass
    
    def create_result(
        self, 
        status: str, 
        result: Dict[str, Any], 
        explanation: str,
        confidence: float = 1.0
    ) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            status=status,
            result=result,
            explanation=explanation,
            timestamp=datetime.now().isoformat(),
            confidence=confidence
        )
    
    def validate_required_fields(
        self, 
        application_data: Dict[str, Any], 
        required_fields: list
    ) -> tuple:
        missing = [f for f in required_fields if f not in application_data or application_data[f] is None]
        if missing:
            return (False, f"Missing required fields: {', '.join(missing)}")
        return (True, "")
