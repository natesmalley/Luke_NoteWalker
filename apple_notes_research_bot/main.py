#!/usr/bin/env python3
"""
Apple Notes Research Bot - Main entry point
Monitors Apple Notes and automatically conducts research on new/changed notes
"""

import asyncio
import signal
import sys
import logging
from pathlib import Path
from typing import Optional

from .config import Config, setup_logging
from .monitor import NotesMonitor
from .analyzer import ContentAnalyzer
from .research_engine import ResearchEngine, ResearchResult
from .formatter import NoteFormatter
from .utils import MetricsTracker, StateManager, validate_environment

logger = logging.getLogger(__name__)

class ResearchBot:
    """Main research bot application"""
    
    def __init__(self, config: Config):
        self.config = config
        self.monitor = NotesMonitor(config.monitor_folders)
        self.analyzer = ContentAnalyzer(config)
        self.research_engine = ResearchEngine(config)
        self.formatter = NoteFormatter()
        self.metrics = MetricsTracker()
        self.state = StateManager()
        self.running = False
        self._shutdown_event = asyncio.Event()
    
    async def process_note(self, note):
        """Process a single note through the research pipeline"""
        logger.info(f"Processing note: {note.name}")
        self.metrics.record_note_processed()
        
        try:
            # Mark as in progress
            self.state.set_in_progress(note.id)
            
            # Step 1: Analyze if research is needed
            logger.debug(f"Analyzing note content...")
            analysis = await self.analyzer.analyze(note.body)
            
            if not analysis.should_research:
                logger.info(f"Note doesn't need research: {analysis.reasoning}")
                self.state.mark_note_processed(note.id, success=True)
                return
            
            logger.info(f"Research needed (confidence: {analysis.confidence:.2f}, category: {analysis.category})")
            
            # Step 2: Conduct research
            logger.debug(f"Conducting research...")
            research_results = await self.research_engine.research(
                note.body,
                analysis.category,
                analysis.research_approach
            )
            
            # Check if research was successful
            successful_results = sum(1 for r in research_results.values() if r.success)
            if successful_results == 0:
                logger.warning("All research providers failed, but attempting fallback formatting")
                # Create a fallback research result
                research_results['fallback'] = ResearchResult(
                    provider='fallback',
                    content=f"""Unable to conduct comprehensive research at this time due to API issues.

Research was requested for: {analysis.category.title()} category content
Confidence: {analysis.confidence:.2f}
Reasoning: {analysis.reasoning}

Please try again later or manually research this topic.""",
                    success=True,  # Mark as success so it gets formatted
                    tokens_used=0
                )
                successful_results = 1
            
            # Step 3: Synthesize results (if multiple providers succeeded)
            synthesized = None
            if successful_results > 1:
                logger.debug("Synthesizing research results...")
                synthesized = await self.research_engine.synthesize_results(research_results)
            
            # Step 4: Format the researched note
            logger.debug("Formatting research results...")
            formatted_note = self.formatter.format_researched_note(
                note,
                analysis,
                research_results,
                synthesized
            )
            
            # Step 5: Update the note
            logger.debug("Updating note with research...")
            success = await self.monitor.update_note(note.id, formatted_note)
            
            if success:
                logger.info(f"✅ Successfully updated note: {note.name}")
                # Track metrics
                total_tokens = sum(r.tokens_used for r in research_results.values())
                self.metrics.record_research(
                    analysis.category, 
                    True, 
                    analysis.confidence,
                    total_tokens
                )
            else:
                logger.error(f"Failed to update note: {note.name}")
                self.metrics.record_research(analysis.category, False, analysis.confidence)
            
            # Mark as processed
            self.state.mark_note_processed(note.id, success=success)
            
        except Exception as e:
            logger.error(f"Error processing note {note.id}: {e}", exc_info=True)
            self.metrics.record_research('unknown', False, 0)
            self.state.mark_note_processed(note.id, success=False)
    
    async def run(self):
        """Main bot loop"""
        self.running = True
        logger.info("🤖 Apple Notes Research Bot starting...")
        logger.info(f"Monitoring folders: {', '.join(self.config.monitor_folders)}")
        logger.info(f"Check interval: {self.config.check_interval} seconds")
        logger.info(f"Confidence threshold: {self.config.research_confidence_threshold}")
        
        try:
            # Check for any in-progress notes from previous run
            in_progress = self.state.get_in_progress()
            if in_progress:
                logger.info(f"Found in-progress note from previous run: {in_progress}")
                # Will be reprocessed in next check
            
            # Start monitoring loop
            async for changed_notes in self.monitor.monitor_loop(self.config.check_interval):
                if not self.running:
                    break
                
                logger.info(f"Found {len(changed_notes)} changed notes")
                
                # Process each changed note
                for note in changed_notes:
                    if not self.running:
                        break
                    
                    # Skip if recently processed (within last hour)
                    if self.state.is_processed(note.id):
                        processed_info = self.state.state['processed_notes'].get(note.id, {})
                        # Parse timestamp and check if recent
                        from datetime import datetime, timedelta
                        if 'processed_at' in processed_info:
                            processed_time = datetime.fromisoformat(processed_info['processed_at'])
                            if datetime.now() - processed_time < timedelta(hours=1):
                                logger.debug(f"Skipping recently processed note: {note.name}")
                                continue
                    
                    await self.process_note(note)
                    
                    # Add small delay between notes to avoid rate limits
                    if self.running:
                        await asyncio.sleep(self.config.rate_limit_delay)
                
                # Check if shutdown was requested
                if self._shutdown_event.is_set():
                    break
            
        except asyncio.CancelledError:
            logger.info("Bot cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
        finally:
            self.running = False
            logger.info("🛑 Research Bot stopped")
            logger.info(self.metrics.get_summary())
    
    def shutdown(self):
        """Gracefully shutdown the bot"""
        logger.info("Shutdown requested...")
        self.running = False
        self._shutdown_event.set()

async def main():
    """Main application entry point"""
    
    # Validate environment
    issues = validate_environment()
    if issues:
        print("❌ Environment validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        print("\nPlease fix these issues before running the bot.")
        sys.exit(1)
    
    # Load configuration
    config = Config.from_file()
    
    # Validate configuration
    config_issues = config.validate()
    if config_issues:
        print("❌ Configuration validation failed:")
        for issue in config_issues:
            print(f"  - {issue}")
        print("\nPlease check your config.json file or environment variables.")
        sys.exit(1)
    
    # Setup logging
    setup_logging(config)
    
    # Create and run bot
    bot = ResearchBot(config)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        bot.shutdown()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the bot
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

def run():
    """Entry point for command line execution"""
    print("""
🪸 CoralCollective Apple Notes Research Bot
=========================================
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    run()