# Error Handling and Fallback Strategies

## Comprehensive Error Resilience Architecture

The Apple Notes Research Bot implements multi-layered error handling to ensure robust operation in production environments. This document outlines the complete error handling strategy, fallback mechanisms, and recovery procedures.

## 1. Error Classification System

### 1.1 Error Categories

**Category 1: Transient Errors** (Recoverable)
- Network connectivity issues
- API rate limiting
- Temporary service unavailability
- AppleScript permission dialogs

**Category 2: Configuration Errors** (Fixable)
- Invalid API keys
- Missing environment variables
- Incorrect file permissions
- Invalid configuration values

**Category 3: System Errors** (Environmental)
- macOS version incompatibility
- Notes.app not available
- Insufficient system resources
- File system access issues

**Category 4: Data Errors** (Content-related)
- Malformed note content
- Unparseable dates
- Invalid JSON responses
- Character encoding issues

**Category 5: Logic Errors** (Code-related)
- Unexpected data types
- Algorithm failures
- State corruption
- Race conditions

### 1.2 Error Severity Levels

```python
class ErrorSeverity:
    CRITICAL = "critical"    # Service stops, immediate attention required
    HIGH = "high"           # Feature fails, degraded operation
    MEDIUM = "medium"       # Partial failure, fallback activated
    LOW = "low"            # Minor issue, logged for analysis
    INFO = "info"          # Informational, no action required
```

## 2. Component-Specific Error Handling

### 2.1 NotesMonitor Error Handling

**AppleScript Execution Errors**:
```python
async def _run_applescript(self, script: str) -> Optional[str]:
    """Execute AppleScript with comprehensive error handling"""
    try:
        process = await asyncio.create_subprocess_exec(
            'osascript', '-e', script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            timeout=30  # Prevent hanging
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode()
            
            # Classify AppleScript errors
            if "AppleScript execution failed" in error_msg:
                logger.warning(f"AppleScript execution failed: {error_msg}")
                return None
            elif "Notes is not running" in error_msg:
                logger.info("Notes app not running, attempting to launch...")
                await self._launch_notes_app()
                return await self._retry_applescript(script)
            elif "permission denied" in error_msg:
                logger.error("AppleScript permission denied. Please grant accessibility permissions.")
                raise AppleScriptPermissionError("Accessibility permissions required")
            else:
                logger.error(f"Unknown AppleScript error: {error_msg}")
                return None
        
        return stdout.decode().strip()
        
    except asyncio.TimeoutError:
        logger.error("AppleScript execution timed out")
        return None
    except Exception as e:
        logger.error(f"Failed to execute AppleScript: {e}")
        return None

async def _retry_applescript(self, script: str, max_retries: int = 3) -> Optional[str]:
    """Retry AppleScript with exponential backoff"""
    for attempt in range(max_retries):
        try:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            result = await self._run_applescript(script)
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"AppleScript retry {attempt + 1} failed: {e}")
    
    logger.error(f"AppleScript failed after {max_retries} retries")
    return None
```

**Note Data Validation**:
```python
def _validate_note_data(self, note_data: Dict) -> bool:
    """Validate note data structure and content"""
    required_fields = ['id', 'name', 'folder', 'creation_date', 'modification_date']
    
    try:
        # Check required fields
        for field in required_fields:
            if field not in note_data:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate data types
        if not isinstance(note_data['id'], str) or not note_data['id']:
            logger.warning("Invalid note ID")
            return False
        
        # Validate dates
        for date_field in ['creation_date', 'modification_date']:
            if not self._is_valid_date_string(note_data[date_field]):
                logger.warning(f"Invalid date format: {date_field}")
                # Try to fix or use current time
                note_data[date_field] = datetime.now().strftime("%A, %B %d, %Y at %I:%M:%S %p")
        
        return True
        
    except Exception as e:
        logger.error(f"Note data validation error: {e}")
        return False

def _sanitize_note_content(self, content: str) -> str:
    """Sanitize note content for safe processing"""
    try:
        # Remove null bytes and control characters
        content = content.replace('\x00', '')
        content = ''.join(char for char in content if ord(char) >= 32 or char in '\n\r\t')
        
        # Limit content size to prevent memory issues
        max_size = 50000  # ~50KB
        if len(content) > max_size:
            logger.warning(f"Note content truncated from {len(content)} to {max_size} characters")
            content = content[:max_size] + "\n\n[Content truncated for processing]"
        
        return content
        
    except Exception as e:
        logger.error(f"Content sanitization error: {e}")
        return "Content sanitization failed"
```

### 2.2 ContentAnalyzer Error Handling

**AI API Error Handling**:
```python
async def analyze(self, content: str) -> AnalysisResult:
    """Analyze content with comprehensive error handling"""
    
    # Input validation
    if not content or len(content.strip()) < 3:
        return AnalysisResult(
            should_research=False,
            confidence=1.0,
            reasoning="Content too short or empty",
            category="none"
        )
    
    # Content preprocessing
    try:
        content = self._preprocess_content(content)
    except Exception as e:
        logger.warning(f"Content preprocessing failed: {e}")
        # Continue with original content
    
    # AI Analysis with fallbacks
    for attempt in range(self.config.max_retries):
        try:
            return await self._analyze_with_ai(content)
            
        except anthropic.RateLimitError as e:
            wait_time = self._calculate_backoff_time(attempt, base_delay=60)
            logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
            await asyncio.sleep(wait_time)
            
        except anthropic.APIConnectionError as e:
            logger.warning(f"API connection error: {e}")
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))
            
        except anthropic.AuthenticationError as e:
            logger.error(f"API authentication failed: {e}")
            # Don't retry authentication errors
            break
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response: {e}")
            # Try again with different prompt formatting
            
        except Exception as e:
            logger.error(f"Unexpected analysis error: {e}")
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_delay)
    
    # All AI attempts failed, use fallback
    logger.info("AI analysis failed, using heuristic fallback")
    return self._fallback_analysis(content)

def _fallback_analysis(self, content: str, category: Optional[str] = None) -> AnalysisResult:
    """Robust heuristic analysis when AI is unavailable"""
    try:
        content_lower = content.lower()
        
        # Enhanced keyword detection
        question_indicators = [
            '?', 'how to', 'what is', 'what are', 'why does', 'why is',
            'when should', 'where can', 'which is', 'best way to',
            'how can i', 'what would', 'should i', 'need to know'
        ]
        
        research_indicators = [
            'research', 'find out', 'look up', 'learn about', 'understand',
            'explore', 'investigate', 'study', 'compare', 'evaluate',
            'ideas for', 'options for', 'alternatives to'
        ]
        
        personal_indicators = [
            'reminder:', 'todo:', 'note to self:', 'remember to',
            'meeting with', 'call with', 'talked to', 'met with',
            'grocery list', 'shopping list', 'password', 'login'
        ]
        
        # Calculate indicators
        question_score = sum(1 for indicator in question_indicators 
                           if indicator in content_lower)
        research_score = sum(1 for indicator in research_indicators 
                           if indicator in content_lower)
        personal_score = sum(1 for indicator in personal_indicators 
                           if indicator in content_lower)
        
        # Determine category if not provided
        if not category:
            category = self._detect_category_keywords(content_lower) or 'general'
        
        # Decision logic
        if personal_score > 0:
            should_research = False
            confidence = 0.9
            reasoning = "Appears to be personal note/reminder"
        elif question_score > 0 or research_score > 0:
            should_research = True
            confidence = min(0.7, 0.4 + (question_score + research_score) * 0.1)
            reasoning = f"Contains {question_score} questions, {research_score} research indicators"
        elif len(content_lower.split()) > 20:
            should_research = True
            confidence = 0.6
            reasoning = "Substantial content that may benefit from research"
        else:
            should_research = False
            confidence = 0.8
            reasoning = "Brief content unlikely to need research"
        
        return AnalysisResult(
            should_research=should_research and confidence >= self.config.research_confidence_threshold,
            confidence=confidence,
            reasoning=f"Heuristic analysis: {reasoning}",
            category=category,
            research_approach="General keyword-based research" if should_research else None
        )
        
    except Exception as e:
        logger.error(f"Fallback analysis failed: {e}")
        return AnalysisResult(
            should_research=False,
            confidence=0.5,
            reasoning="Analysis failed, skipping research",
            category="unknown"
        )
```

### 2.3 ResearchEngine Error Handling

**Multi-Provider Error Handling**:
```python
async def research(self, content: str, category: str, 
                   research_approach: Optional[str] = None) -> Dict[str, ResearchResult]:
    """Conduct research with comprehensive error handling"""
    
    results = {}
    
    # Validate inputs
    if not content.strip():
        logger.warning("Empty research content provided")
        return {
            "error": ResearchResult("system", "", False, "No content to research")
        }
    
    # Prepare research prompt
    try:
        prompt = self._prepare_research_prompt(content, category, research_approach)
    except Exception as e:
        logger.error(f"Failed to prepare research prompt: {e}")
        return {
            "error": ResearchResult("system", "", False, "Prompt preparation failed")
        }
    
    # Execute research with parallel or sequential processing
    if self.config.parallel_research:
        results = await self._parallel_research(prompt, category)
    else:
        results = await self._sequential_research(prompt, category)
    
    # Validate results
    successful_results = [r for r in results.values() if r.success]
    if not successful_results:
        logger.warning("All research providers failed")
        # Return partial results with error information
    
    return results

async def _parallel_research(self, prompt: str, category: str) -> Dict[str, ResearchResult]:
    """Parallel research execution with error isolation"""
    
    tasks = [
        self._research_with_timeout("claude", self._research_claude, prompt, category),
        self._research_with_timeout("openai", self._research_openai, prompt, category)
    ]
    
    results = {}
    completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, result in enumerate(completed_tasks):
        provider = ["claude", "openai"][i]
        
        if isinstance(result, Exception):
            logger.error(f"{provider} research failed: {result}")
            results[provider] = ResearchResult(
                provider=provider,
                content="",
                success=False,
                error=str(result)
            )
        else:
            results[provider] = result
    
    return results

async def _research_with_timeout(self, provider: str, research_func, 
                                prompt: str, category: str) -> ResearchResult:
    """Execute research with timeout protection"""
    try:
        return await asyncio.wait_for(
            research_func(prompt, category),
            timeout=self.config.max_research_time
        )
    except asyncio.TimeoutError:
        logger.warning(f"{provider} research timed out after {self.config.max_research_time}s")
        return ResearchResult(
            provider=provider,
            content="",
            success=False,
            error="Research timed out"
        )

async def _research_claude_with_retry(self, prompt: str, category: str) -> ResearchResult:
    """Claude research with retry logic"""
    
    for attempt in range(self.config.max_retries):
        try:
            return await self._research_claude(prompt, category)
            
        except anthropic.RateLimitError as e:
            if attempt < self.config.max_retries - 1:
                wait_time = self._calculate_backoff_time(attempt, base_delay=60)
                logger.warning(f"Claude rate limited, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
            else:
                return ResearchResult("claude", "", False, f"Rate limit exceeded: {e}")
                
        except anthropic.APIConnectionError as e:
            if attempt < self.config.max_retries - 1:
                wait_time = self._calculate_backoff_time(attempt, base_delay=5)
                logger.warning(f"Claude connection error, retrying in {wait_time}s")
                await asyncio.sleep(wait_time)
            else:
                return ResearchResult("claude", "", False, f"Connection failed: {e}")
                
        except anthropic.AuthenticationError as e:
            logger.error(f"Claude authentication failed: {e}")
            return ResearchResult("claude", "", False, f"Authentication error: {e}")
            
        except Exception as e:
            logger.error(f"Claude research error: {e}")
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_delay)
            else:
                return ResearchResult("claude", "", False, f"Research failed: {e}")
    
    return ResearchResult("claude", "", False, "Max retries exceeded")

def _calculate_backoff_time(self, attempt: int, base_delay: float = 2.0, 
                           max_delay: float = 300.0) -> float:
    """Calculate exponential backoff with jitter"""
    import random
    
    delay = min(base_delay * (2 ** attempt), max_delay)
    # Add jitter (±25%)
    jitter = delay * 0.25 * (2 * random.random() - 1)
    return max(1.0, delay + jitter)
```

### 2.4 State Management Error Handling

**State Persistence Error Handling**:
```python
class StateManager:
    def save_state(self):
        """Save state with atomic write and backup"""
        try:
            # Prepare state data
            state_data = {
                'last_run': datetime.now().isoformat(),
                'processed_notes': self.state['processed_notes'],
                'in_progress': self.state.get('in_progress'),
                'version': '1.0'
            }
            
            # Atomic write using temporary file
            temp_file = self.state_file.with_suffix('.tmp')
            backup_file = self.state_file.with_suffix('.backup')
            
            # Create backup if original exists
            if self.state_file.exists():
                shutil.copy2(self.state_file, backup_file)
            
            # Write to temporary file
            with open(temp_file, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            # Atomic rename
            temp_file.replace(self.state_file)
            
            logger.debug("State saved successfully")
            
        except PermissionError as e:
            logger.error(f"Permission denied saving state: {e}")
            # Try alternative location
            self._try_alternative_state_location()
            
        except OSError as e:
            logger.error(f"OS error saving state: {e}")
            # Continue operation without state persistence
            
        except Exception as e:
            logger.error(f"Unexpected error saving state: {e}")
            # Attempt recovery from backup
            self._recover_from_backup()

    def _load_state(self) -> Dict[str, Any]:
        """Load state with corruption recovery"""
        for state_file in [self.state_file, self.state_file.with_suffix('.backup')]:
            if not state_file.exists():
                continue
                
            try:
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    
                # Validate state data
                if self._validate_state_data(data):
                    logger.info(f"Loaded state from {state_file}")
                    return data
                else:
                    logger.warning(f"Invalid state data in {state_file}")
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Corrupted state file {state_file}: {e}")
                
            except Exception as e:
                logger.error(f"Error loading state from {state_file}: {e}")
        
        # No valid state found, return default
        logger.info("No valid state found, starting fresh")
        return self._create_default_state()

    def _validate_state_data(self, data: Dict) -> bool:
        """Validate state data structure"""
        try:
            required_keys = ['processed_notes']
            for key in required_keys:
                if key not in data:
                    return False
            
            # Validate processed_notes structure
            if not isinstance(data['processed_notes'], dict):
                return False
                
            return True
            
        except Exception:
            return False
```

## 3. System-Level Error Handling

### 3.1 Application Lifecycle Error Management

**Startup Error Handling**:
```python
async def main():
    """Main application with comprehensive startup error handling"""
    try:
        # Environment validation
        issues = validate_environment()
        if issues:
            logger.error("Environment validation failed:")
            for issue in issues:
                logger.error(f"  - {issue}")
            
            # Attempt automatic fixes where possible
            auto_fixed = await attempt_auto_fixes(issues)
            remaining_issues = [i for i in issues if i not in auto_fixed]
            
            if remaining_issues:
                print_user_instructions(remaining_issues)
                sys.exit(1)
        
        # Configuration loading with validation
        try:
            config = Config.from_file()
            config_issues = config.validate()
            
            if config_issues:
                logger.error("Configuration validation failed:")
                for issue in config_issues:
                    logger.error(f"  - {issue}")
                
                # Attempt configuration repair
                repaired_config = attempt_config_repair(config, config_issues)
                if repaired_config:
                    config = repaired_config
                    logger.info("Configuration automatically repaired")
                else:
                    sys.exit(1)
                    
        except Exception as e:
            logger.error(f"Configuration loading failed: {e}")
            config = create_minimal_config()
            logger.info("Using minimal fallback configuration")
        
        # Setup logging
        setup_logging(config.log_level, config.log_file)
        
        # Initialize bot with error handling
        try:
            bot = ResearchBot(config)
        except Exception as e:
            logger.error(f"Bot initialization failed: {e}")
            sys.exit(1)
        
        # Setup signal handlers
        setup_signal_handlers(bot)
        
        # Run with recovery mechanism
        await run_with_recovery(bot)
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

async def run_with_recovery(bot: ResearchBot):
    """Run bot with automatic recovery on crashes"""
    max_crashes = 3
    crash_count = 0
    
    while crash_count < max_crashes:
        try:
            await bot.run()
            break  # Normal exit
            
        except Exception as e:
            crash_count += 1
            logger.error(f"Bot crashed ({crash_count}/{max_crashes}): {e}", exc_info=True)
            
            if crash_count < max_crashes:
                # Wait before restart
                wait_time = min(60 * crash_count, 300)  # Max 5 minutes
                logger.info(f"Restarting in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                
                # Attempt to clear any corrupted state
                try:
                    bot.state.clear_in_progress()
                    logger.info("Cleared potentially corrupted state")
                except:
                    pass
            else:
                logger.error("Max crash limit reached, exiting")
                raise
```

### 3.2 Resource Management

**Memory Management**:
```python
class ResourceManager:
    def __init__(self):
        self.memory_threshold = 500 * 1024 * 1024  # 500MB
        self.last_gc_time = time.time()
        
    async def check_resources(self):
        """Monitor resource usage and take action if needed"""
        try:
            import psutil
            process = psutil.Process()
            memory_usage = process.memory_info().rss
            
            if memory_usage > self.memory_threshold:
                logger.warning(f"High memory usage: {memory_usage / 1024 / 1024:.1f}MB")
                await self._cleanup_memory()
                
        except ImportError:
            # psutil not available, use basic Python memory tracking
            pass
        except Exception as e:
            logger.warning(f"Resource check failed: {e}")
    
    async def _cleanup_memory(self):
        """Attempt memory cleanup"""
        try:
            import gc
            
            # Force garbage collection
            collected = gc.collect()
            logger.info(f"Garbage collection freed {collected} objects")
            
            self.last_gc_time = time.time()
            
        except Exception as e:
            logger.warning(f"Memory cleanup failed: {e}")
```

## 4. Recovery Mechanisms

### 4.1 Crash Recovery

**State Recovery on Restart**:
```python
async def recover_from_crash(self):
    """Recover from previous crash"""
    try:
        # Check for in-progress operations
        in_progress = self.state.get_in_progress()
        
        if in_progress:
            logger.info(f"Found in-progress note from crash: {in_progress}")
            
            # Try to recover note information
            try:
                note = await self.monitor.get_note_by_id(in_progress)
                if note:
                    logger.info(f"Recovering processing for note: {note.name}")
                    # Reprocess the note
                    await self.process_note(note)
                else:
                    logger.warning(f"Could not recover note {in_progress}")
                    
            except Exception as e:
                logger.error(f"Recovery failed for note {in_progress}: {e}")
            finally:
                # Clear in-progress state
                self.state.mark_note_processed(in_progress, success=False)
        
        # Check for partially processed notes
        await self._recover_partial_processing()
        
    except Exception as e:
        logger.error(f"Crash recovery failed: {e}")
        # Continue with normal operation
```

### 4.2 Data Corruption Recovery

**Configuration Recovery**:
```python
def recover_configuration(self):
    """Recover from configuration corruption"""
    try:
        # Try backup configuration
        backup_config = self.config_file.with_suffix('.backup')
        if backup_config.exists():
            logger.info("Attempting configuration recovery from backup")
            shutil.copy2(backup_config, self.config_file)
            return Config.from_file()
            
        # Create minimal working configuration
        logger.info("Creating minimal configuration")
        minimal_config = Config()
        
        # Try to preserve API keys if available
        minimal_config._load_api_keys()
        
        # Save minimal config
        minimal_config.save()
        
        return minimal_config
        
    except Exception as e:
        logger.error(f"Configuration recovery failed: {e}")
        raise ConfigurationError("Cannot recover configuration")
```

## 5. Monitoring and Alerting

### 5.1 Health Checks

**System Health Monitoring**:
```python
class HealthMonitor:
    def __init__(self):
        self.last_successful_operation = datetime.now()
        self.error_count = 0
        self.max_error_threshold = 10
        
    def record_success(self):
        """Record successful operation"""
        self.last_successful_operation = datetime.now()
        self.error_count = max(0, self.error_count - 1)  # Decay error count
        
    def record_error(self, severity: str = "medium"):
        """Record error occurrence"""
        self.error_count += 1
        
        if self.error_count >= self.max_error_threshold:
            logger.critical(f"Error threshold exceeded: {self.error_count} errors")
            # Could trigger alerts or shutdown
            
    def get_health_status(self) -> Dict:
        """Get current health status"""
        time_since_success = datetime.now() - self.last_successful_operation
        
        return {
            'healthy': time_since_success.total_seconds() < 3600 and self.error_count < 5,
            'last_success': self.last_successful_operation.isoformat(),
            'error_count': self.error_count,
            'uptime': time_since_success.total_seconds()
        }
```

### 5.2 Error Reporting

**Comprehensive Error Logging**:
```python
class ErrorReporter:
    def __init__(self):
        self.error_log = Path("error_report.json")
        
    def report_error(self, error: Exception, context: Dict, severity: str = "medium"):
        """Report error with full context"""
        error_report = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'severity': severity,
            'context': context,
            'traceback': traceback.format_exc(),
            'system_info': self._get_system_info()
        }
        
        # Log to structured error file
        try:
            existing_errors = []
            if self.error_log.exists():
                with open(self.error_log, 'r') as f:
                    existing_errors = json.load(f)
                    
            existing_errors.append(error_report)
            
            # Keep only last 100 errors
            existing_errors = existing_errors[-100:]
            
            with open(self.error_log, 'w') as f:
                json.dump(existing_errors, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to write error report: {e}")
    
    def _get_system_info(self) -> Dict:
        """Get system information for error context"""
        try:
            import platform
            return {
                'python_version': platform.python_version(),
                'system': platform.system(),
                'release': platform.release(),
                'machine': platform.machine()
            }
        except:
            return {}
```

## 6. Best Practices Summary

### 6.1 Error Handling Principles

1. **Fail Fast, Recover Gracefully**: Detect errors early but provide fallbacks
2. **Preserve User Data**: Never lose user notes or research results
3. **Provide Clear Feedback**: Log errors with actionable information
4. **Maintain Service Availability**: Continue operation when possible
5. **Learn from Failures**: Track error patterns for improvement

### 6.2 Implementation Guidelines

1. **Always use try/except blocks** for external API calls
2. **Implement timeouts** for all async operations
3. **Provide fallback mechanisms** for critical functionality
4. **Log errors with context** for debugging
5. **Test error paths** as thoroughly as success paths
6. **Monitor error rates** and trends
7. **Implement circuit breakers** for external dependencies

This comprehensive error handling strategy ensures the Apple Notes Research Bot operates reliably in production environments while providing clear diagnostics and recovery mechanisms for all failure scenarios.