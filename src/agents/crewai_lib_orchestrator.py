"""
CrewAI Orchestrator - Uses actual CrewAI library for multi-agent orchestration

NOTE: CrewAI requires OpenAI API key to work. 
For now, we use our custom orchestrator which works like CrewAI.

To enable CrewAI:
1. Set OPENAI_API_KEY environment variable
2. Install all dependencies: pip install crewai crewai-tools openai pydantic-settings
3. Run with --use-crewai flag
"""
from typing import Dict, Any, List
import os
import json
from datetime import datetime

# Check if CrewAI can be imported
try:
    from crewai import Agent, Task, Crew, Process
    CREWAI_AVAILABLE = os.environ.get('OPENAI_API_KEY') is not None
except ImportError:
    CREWAI_AVAILABLE = False

class CrewAIBasedOrchestrator:
    def __init__(self, data_loader=None):
        self.data_loader = data_loader
        self.agents = {}
        self.use_crewai = CREWAI_AVAILABLE
        
        if self.use_crewai:
            self._setup_agents()
        else:
            print("[Orchestrator] Using custom multi-agent system (CrewAI-style)")
    
    def _setup_agents(self):
        """Setup CrewAI agents"""
        self.policy_agent = Agent(
            role="Policy Expert",
            goal="Determine if farmer is eligible for agricultural schemes",
            backstory="You are a senior policy expert at Agriculture Department.",
            verbose=True
        )
        # ... rest of setup
    
    def process(self, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process application - uses custom orchestrator"""
        
        # Use our existing custom orchestrator
        from src.agents.crewai_orchestrator import CrewAIOrchestrator
        
        orchestrator = CrewAIOrchestrator(self.data_loader)
        result = orchestrator.process(application_data)
        
        return result.to_dict()


def create_crewai_orchestrator(data_loader=None):
    """Factory function - returns appropriate orchestrator"""
    
    if os.environ.get('OPENAI_API_KEY'):
        try:
            from crewai_lib_orchestrator import CrewAIBasedOrchestrator
            return CrewAIBasedOrchestrator(data_loader)
        except:
            pass
    
    # Default: use custom orchestrator
    from src.agents.crewai_orchestrator import CrewAIOrchestrator
    return CrewAIOrchestrator(data_loader)
