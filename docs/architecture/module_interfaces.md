# Apple Notes Research Bot - Module Interfaces and Structure

## Component Interface Specifications

### 1. Core Module Structure

```
apple_notes_research_bot/
├── __init__.py              # Package initialization
├── main.py                  # ResearchBot orchestrator
├── config.py                # Configuration management
├── monitor.py               # Apple Notes integration
├── analyzer.py              # Content analysis engine
├── research_engine.py       # Multi-provider AI research
├── formatter.py             # Research output formatting
├── utils.py                 # Utilities and metrics
└── requirements.txt         # Dependencies
```

### 2. Interface Definitions

#### 2.1 ResearchBot (main.py)

**Primary Interface**:
```python
class ResearchBot:
    def __init__(self, config: Config) -> None
    async def process_note(self, note: Note) -> None
    async def run(self) -> None  
    def shutdown(self) -> None

# Entry Points
async def main() -> None
def run() -> None  # CLI entry point
```

**Dependencies**:
- `Config` from config.py
- `NotesMonitor` from monitor.py
- `ContentAnalyzer` from analyzer.py
- `ResearchEngine` from research_engine.py
- `NoteFormatter` from formatter.py
- `MetricsTracker`, `StateManager` from utils.py

#### 2.2 NotesMonitor (monitor.py)

**Data Models**:
```python
@dataclass
class Note:
    id: str                    # Apple Notes unique identifier
    name: str                  # Note title
    body: str                  # Note content
    folder: str                # Parent folder name
    creation_date: datetime    # Original creation timestamp
    modification_date: datetime # Last modification timestamp
    content_hash: str          # SHA256 hash for change detection
    
    def calculate_hash(self) -> str
    def has_changed(self, other: "Note") -> bool
```

**Primary Interface**:
```python
class NotesMonitor:
    def __init__(self, folders: List[str] = None) -> None
    async def get_all_notes(self) -> List[Note]
    async def check_for_changes(self) -> List[Note]  
    async def update_note(self, note_id: str, content: str) -> bool
    async def monitor_loop(self, interval: int) -> AsyncGenerator[List[Note]]
    
    # Private methods
    async def _get_note_body(self, note_id: str) -> Optional[str]
    async def _run_applescript(self, script: str) -> Optional[str]
    def _parse_applescript_date(self, date_str: str) -> datetime
    def _load_state(self) -> None
    def _save_state(self) -> None
```

**AppleScript Interface**:
- Returns JSON-formatted note data
- Handles date parsing and content escaping
- Manages folder-based filtering

#### 2.3 ContentAnalyzer (analyzer.py)

**Data Models**:
```python
@dataclass
class AnalysisResult:
    should_research: bool      # Research recommendation
    confidence: float          # Confidence score (0.0-1.0)
    reasoning: str             # Human-readable explanation
    category: str              # Research category classification
    research_approach: Optional[str]  # Recommended research strategy
```

**Primary Interface**:
```python
class ContentAnalyzer:
    def __init__(self, config: Config) -> None
    async def analyze(self, content: str) -> AnalysisResult
    
    # Support methods
    def _detect_category_keywords(self, content: str) -> Optional[str]
    def _fallback_analysis(self, content: str) -> AnalysisResult
    def is_personal_note(self, content: str) -> bool
```

**Category Classification**:
- `software`: Development, APIs, technical questions
- `ai`: Machine learning, LLMs, data science
- `building`: Construction, DIY, materials
- `lifestyle`: Activities, entertainment, travel
- `productivity`: Workflow, time management
- `general`: Information queries

#### 2.4 ResearchEngine (research_engine.py)

**Data Models**:
```python
@dataclass
class ResearchResult:
    provider: str              # "claude" or "openai"
    content: str               # Research findings
    success: bool              # Operation success flag
    error: Optional[str]       # Error message if failed
    tokens_used: int           # Token count for billing/limits
```

**Primary Interface**:
```python
class ResearchEngine:
    def __init__(self, config: Config) -> None
    async def research(self, content: str, category: str, 
                       approach: Optional[str] = None) -> Dict[str, ResearchResult]
    async def synthesize_results(self, results: Dict[str, ResearchResult]) -> str
    
    # Provider-specific methods
    async def _research_claude(self, prompt: str, category: str) -> ResearchResult
    async def _research_openai(self, prompt: str, category: str) -> ResearchResult
```

**Provider Configuration**:
- Parallel execution by default
- Category-specific prompts and system messages
- Token limits and rate limiting
- Error handling with fallbacks

#### 2.5 NoteFormatter (formatter.py)

**Primary Interface**:
```python
class NoteFormatter:
    def __init__(self) -> None
    def format_researched_note(self, note: Note, analysis: AnalysisResult,
                               research_results: Dict[str, ResearchResult],
                               synthesized: Optional[str] = None) -> str
    
    # Support methods
    def _generate_title(self, note: Note, analysis: AnalysisResult) -> str
    def _format_research_findings(self, results: Dict[str, ResearchResult]) -> str
    def _extract_insights(self, content: str) -> str
    def _extract_resources(self, content: str) -> str
    def preserve_original_formatting(self, original: str, research: str) -> str
```

**Template System**:
- Category-specific formatting templates
- Structured sections with emoji indicators
- Automatic insight and resource extraction
- Timestamp and attribution tracking

#### 2.6 Configuration (config.py)

**Data Model**:
```python
@dataclass
class Config:
    # API Keys
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    # Monitoring settings
    check_interval: int = 30
    monitor_folders: List[str] = field(default_factory=lambda: ["Notes"])
    
    # Research settings  
    research_confidence_threshold: float = 0.7
    max_research_time: int = 60
    parallel_research: bool = True
    
    # AI Model settings
    claude_analysis_model: str = "claude-3-haiku-20240307"
    claude_research_model: str = "claude-3-sonnet-20240229"
    openai_model: str = "gpt-4"
    
    # Token limits
    max_analysis_tokens: int = 300
    max_research_tokens: int = 800
    
    # Categories
    research_categories: List[str] = field(default_factory=lambda: [
        "software", "ai", "building", "lifestyle", "productivity", "general"
    ])
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "research_bot.log"
    
    # Storage
    state_file: str = ".research_bot_state.json"
    processed_notes_cache: str = ".processed_notes_cache.json"
    
    # Rate limiting
    rate_limit_delay: float = 1.0
    max_retries: int = 3
    retry_delay: float = 2.0
```

**Configuration Interface**:
```python
class Config:
    @classmethod
    def from_file(cls, config_file: str = "config.json") -> "Config"
    def validate(self) -> List[str]
    def save_api_keys_to_keychain(self) -> None
    def to_dict(self) -> Dict
    def save(self, filepath: Optional[str] = None) -> None
    
    # Private methods
    def _load_api_keys(self) -> None
```

#### 2.7 Utilities (utils.py)

**MetricsTracker Interface**:
```python
class MetricsTracker:
    def __init__(self, metrics_file: str = "research_bot_metrics.json") -> None
    def record_note_processed(self) -> None
    def record_research(self, category: str, success: bool, 
                        confidence: float, tokens: int = 0) -> None
    def record_api_error(self, provider: str) -> None
    def get_summary(self) -> str
    
    # Private methods
    def _load_metrics(self) -> Dict[str, Any]
    def save_metrics(self) -> None
```

**StateManager Interface**:
```python
class StateManager:
    def __init__(self, state_file: str = ".research_bot_state.json") -> None
    def mark_note_processed(self, note_id: str, success: bool = True) -> None
    def set_in_progress(self, note_id: str) -> None
    def get_in_progress(self) -> Optional[str]
    def is_processed(self, note_id: str) -> bool
    
    # Private methods
    def _load_state(self) -> Dict[str, Any]
    def save_state(self) -> None
```

**Utility Functions**:
```python
def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None
def validate_environment() -> List[str]
```

### 3. Data Flow Interfaces

#### 3.1 Note Processing Pipeline

```
Note (monitor.py) 
    ↓
AnalysisResult (analyzer.py)
    ↓  
Dict[str, ResearchResult] (research_engine.py)
    ↓
Optional[str] (synthesized research)
    ↓
str (formatted note content) (formatter.py)
    ↓
bool (update success) (monitor.py)
```

#### 3.2 Configuration Flow

```
Environment Variables
    ↓
config.json file
    ↓
macOS Keychain (API keys)
    ↓
Config object
    ↓
Component initialization
```

#### 3.3 State Management Flow

```
Application Start
    ↓
Load previous state
    ↓
Check in-progress notes
    ↓
Process notes
    ↓
Update state after each operation
    ↓
Persist state on shutdown
```

### 4. External Interface Contracts

#### 4.1 Apple Notes AppleScript Interface

**Input**: AppleScript commands for Notes.app
**Output**: JSON-formatted note data or success/failure status

**Note Retrieval Contract**:
```json
{
  "id": "x-coredata://note-uuid",
  "name": "Note Title", 
  "folder": "Folder Name",
  "creation_date": "Monday, December 4, 2024 at 3:30:00 PM",
  "modification_date": "Monday, December 4, 2024 at 3:30:00 PM"
}
```

**Note Update Contract**:
- Input: Note ID and escaped content string
- Output: Boolean success indicator
- Side Effect: Note content updated in Apple Notes, synced via iCloud

#### 4.2 Anthropic Claude API Interface

**Analysis Request**:
```python
{
    "model": "claude-3-haiku-20240307",
    "max_tokens": 300,
    "temperature": 0.3,
    "messages": [{"role": "user", "content": analysis_prompt}]
}
```

**Research Request**:
```python  
{
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 800,
    "temperature": 0.7,
    "system": category_specific_system_prompt,
    "messages": [{"role": "user", "content": research_prompt}]
}
```

#### 4.3 OpenAI API Interface

**Research Request**:
```python
{
    "model": "gpt-4",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": research_prompt}
    ],
    "max_tokens": 800,
    "temperature": 0.7
}
```

### 5. Error Handling Interfaces

#### 5.1 Exception Hierarchy

```python
# Custom exceptions (if defined)
class AppleScriptError(Exception): pass
class AnalysisError(Exception): pass
class ResearchError(Exception): pass
class ConfigurationError(Exception): pass

# Standard exceptions handled
- anthropic.APIError
- openai.APIError  
- json.JSONDecodeError
- asyncio.CancelledError
- KeyboardInterrupt
```

#### 5.2 Error Response Contracts

**Analysis Failure**:
- Returns AnalysisResult with should_research=False
- Includes error reasoning in reasoning field
- Falls back to keyword-based heuristics

**Research Failure**:
- Returns ResearchResult with success=False
- Includes error message in error field
- Continues with partial results if one provider succeeds

**Update Failure**:  
- Returns False from update_note()
- Logs error details
- Preserves original note content

### 6. Performance Interface Contracts

#### 6.1 Async Operation Contracts

All I/O operations must be async:
- AppleScript execution: `async def _run_applescript()`
- AI API calls: `async def _research_claude()`  
- File operations: Use aiofiles if needed
- Sleep operations: `await asyncio.sleep()`

#### 6.2 Resource Management

**Memory Management**:
- Notes processed individually to avoid memory accumulation
- Research results cleared after processing
- State persisted incrementally

**API Rate Limiting**:
- 1-second delay between API calls
- Parallel execution where supported
- Exponential backoff on rate limit errors

### 7. Testing Interfaces

#### 7.1 Mock Interfaces for Testing

**AppleScript Mock**:
```python
class MockAppleScript:
    async def run_script(self, script: str) -> str
    def set_notes(self, notes: List[Dict]) -> None
```

**AI Provider Mocks**:
```python
class MockClaudeProvider:
    async def analyze(self, content: str) -> str
    async def research(self, prompt: str) -> str

class MockOpenAIProvider:
    async def research(self, prompt: str) -> str
```

#### 7.2 Test Data Interfaces

**Sample Note Data**:
```python
SAMPLE_NOTES = [
    {
        "id": "test-note-1",
        "name": "Python API Testing",
        "body": "How do I test async APIs in Python?",
        "folder": "Notes"
    }
]
```

### 8. Deployment Interface

#### 8.1 Installation Requirements

**System Dependencies**:
- macOS 10.14+ (for AppleScript Notes access)
- Python 3.8+ with asyncio support
- Network access for AI APIs

**Permission Requirements**:
- AppleScript access to Notes.app
- Keychain access (optional, for secure API key storage)
- File system access for state and logs

#### 8.2 Configuration Interface

**Environment Variables**:
```bash
ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=sk-...
CORAL_CHECK_INTERVAL=30
CORAL_CONFIDENCE_THRESHOLD=0.7
CORAL_LOG_LEVEL=INFO
```

**Configuration File Interface**:
```json
{
  "check_interval": 30,
  "research_confidence_threshold": 0.7,
  "monitor_folders": ["Notes", "Research"],
  "log_level": "INFO",
  "log_file": "research_bot.log",
  "parallel_research": true,
  "rate_limit_delay": 1.0
}
```

This interface specification provides complete contracts for all module interactions, enabling independent development and testing of each component while ensuring proper integration across the entire system.