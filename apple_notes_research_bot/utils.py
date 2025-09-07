"""
Utility functions and logging setup
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import json
from datetime import datetime

def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Configure logging for the application"""
    
    # Create logs directory if needed
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(exist_ok=True, parents=True)
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )
    
    # Set specific library log levels to reduce noise
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('anthropic').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

class MetricsTracker:
    """Track metrics for the research bot"""
    
    def __init__(self, metrics_file: str = "research_bot_metrics.json"):
        self.metrics_file = Path(metrics_file)
        self.metrics = self._load_metrics()
    
    def _load_metrics(self) -> Dict[str, Any]:
        """Load existing metrics from file"""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Initialize default metrics
        return {
            'start_time': datetime.now().isoformat(),
            'total_notes_processed': 0,
            'total_research_conducted': 0,
            'successful_researches': 0,
            'failed_researches': 0,
            'categories': {},
            'api_errors': {'claude': 0, 'openai': 0},
            'average_confidence': 0,
            'total_tokens_used': 0
        }
    
    def save_metrics(self):
        """Save metrics to file"""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save metrics: {e}")
    
    def record_note_processed(self):
        """Record that a note was processed"""
        self.metrics['total_notes_processed'] += 1
        self.save_metrics()
    
    def record_research(self, category: str, success: bool, confidence: float, tokens: int = 0):
        """Record research operation"""
        self.metrics['total_research_conducted'] += 1
        
        if success:
            self.metrics['successful_researches'] += 1
        else:
            self.metrics['failed_researches'] += 1
        
        # Track by category
        if category not in self.metrics['categories']:
            self.metrics['categories'][category] = {'count': 0, 'successful': 0}
        
        self.metrics['categories'][category]['count'] += 1
        if success:
            self.metrics['categories'][category]['successful'] += 1
        
        # Update average confidence
        total = self.metrics['total_research_conducted']
        current_avg = self.metrics['average_confidence']
        self.metrics['average_confidence'] = ((current_avg * (total - 1)) + confidence) / total
        
        # Track tokens
        self.metrics['total_tokens_used'] += tokens
        
        self.save_metrics()
    
    def record_api_error(self, provider: str):
        """Record an API error"""
        if provider in self.metrics['api_errors']:
            self.metrics['api_errors'][provider] += 1
            self.save_metrics()
    
    def get_summary(self) -> str:
        """Get a summary of metrics"""
        summary = f"""
Research Bot Metrics Summary
============================
Running since: {self.metrics['start_time']}
Total notes processed: {self.metrics['total_notes_processed']}
Total research conducted: {self.metrics['total_research_conducted']}
Success rate: {self.metrics['successful_researches']}/{self.metrics['total_research_conducted']} 
Average confidence: {self.metrics['average_confidence']:.2f}
Total tokens used: {self.metrics['total_tokens_used']}

Categories:
"""
        for category, data in self.metrics['categories'].items():
            success_rate = (data['successful'] / data['count'] * 100) if data['count'] > 0 else 0
            summary += f"  {category}: {data['count']} researches ({success_rate:.0f}% success)\n"
        
        summary += f"\nAPI Errors:\n"
        for provider, count in self.metrics['api_errors'].items():
            summary += f"  {provider}: {count} errors\n"
        
        return summary

class StateManager:
    """Manage application state and recovery"""
    
    def __init__(self, state_file: str = ".research_bot_state.json"):
        self.state_file = Path(state_file)
        self.state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load application state"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {
            'last_run': None,
            'processed_notes': {},
            'in_progress': None
        }
    
    def save_state(self):
        """Save application state"""
        self.state['last_run'] = datetime.now().isoformat()
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save state: {e}")
    
    def mark_note_processed(self, note_id: str, success: bool = True):
        """Mark a note as processed"""
        self.state['processed_notes'][note_id] = {
            'processed_at': datetime.now().isoformat(),
            'success': success
        }
        
        # Clear in-progress if this was it
        if self.state['in_progress'] == note_id:
            self.state['in_progress'] = None
        
        self.save_state()
    
    def set_in_progress(self, note_id: str):
        """Mark a note as being processed"""
        self.state['in_progress'] = note_id
        self.save_state()
    
    def get_in_progress(self) -> Optional[str]:
        """Get the note currently being processed"""
        return self.state.get('in_progress')
    
    def is_processed(self, note_id: str) -> bool:
        """Check if a note has been processed"""
        return note_id in self.state['processed_notes']

def validate_environment() -> list:
    """Validate the environment is properly configured"""
    issues = []
    
    # Check for API keys
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        try:
            import keyring
            if not keyring.get_password("coral_collective", "anthropic_api_key"):
                issues.append("Missing Anthropic API key (set ANTHROPIC_API_KEY env var)")
        except:
            issues.append("Missing Anthropic API key (set ANTHROPIC_API_KEY env var)")
    
    if not os.getenv('OPENAI_API_KEY'):
        try:
            import keyring
            if not keyring.get_password("coral_collective", "openai_api_key"):
                issues.append("Missing OpenAI API key (set OPENAI_API_KEY env var)")
        except:
            issues.append("Missing OpenAI API key (set OPENAI_API_KEY env var)")
    
    # Check for macOS
    import platform
    if platform.system() != 'Darwin':
        issues.append("This bot requires macOS for Apple Notes integration")
    
    # Check for required Python packages
    required_packages = ['anthropic', 'openai', 'asyncio']
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            issues.append(f"Missing required package: {package}")
    
    return issues