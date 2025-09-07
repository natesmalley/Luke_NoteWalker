# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Luke_NoteWalker is an Apple Notes Research Bot that monitors Apple Notes folders and automatically conducts AI-powered research on new or changed notes. It integrates with the CoralCollective framework and uses multiple AI providers (Claude, OpenAI) to generate comprehensive research results.

## Key Commands

### Running the Application

```bash
# Install dependencies
pip install -r apple_notes_research_bot/requirements.txt

# Run the research bot
python -m apple_notes_research_bot

# Run the multi-agent system demo
python apple_notes_research_bot/test_multi_agent_example.py
```

### Environment Setup

Required environment variables or macOS keychain entries:
- `ANTHROPIC_API_KEY` - For Claude AI integration
- `OPENAI_API_KEY` - For OpenAI integration

## Architecture

### Core Components

1. **NotesMonitor** (`monitor.py`) - Monitors Apple Notes via AppleScript for changes
2. **ContentAnalyzer** (`analyzer.py`) - AI-powered analysis with confidence scoring (0.7 threshold)
3. **ResearchEngine** (`research_engine.py`) - Multi-provider parallel research execution
4. **NoteFormatter** (`formatter.py`) - Professional formatting of research results
5. **MultiAgentResearchSystem** (`multi_agent_system.py`) - Advanced multi-domain research orchestration

### Research Categories

- Software Development (APIs, frameworks, technical implementation)
- AI/ML (Machine learning, models, data science)
- Building/Construction (DIY projects, materials, tools)
- Lifestyle (Activities, entertainment, travel, food)
- Productivity (Workflow optimization, time management)
- General (Information queries and research topics)

### Key Technical Details

- **Platform**: macOS 10.14+ required (Apple Notes AppleScript integration)
- **Python**: 3.8+ with async/await support
- **Monitoring**: 30-second intervals with hash-based change detection
- **Rate Limiting**: 1-second delay between API calls
- **State Management**: Persistent state with crash recovery
- **Error Handling**: Comprehensive fallback strategies throughout

### Configuration

Configuration is managed through:
- Environment variables
- `config.json` file (if present)
- macOS keychain for secure API key storage

Default settings in `config.py`:
- `check_interval`: 30 seconds
- `research_confidence_threshold`: 0.7
- `rate_limit_delay`: 1 second
- `monitor_folders`: ["Research Notes"]

## CoralCollective Integration

The project is designed to integrate with the CoralCollective framework:
- Compatible with agent runner patterns
- Follows provider system architecture
- Implements shared design patterns for error handling and state management
- Multi-agent orchestration support via `MultiAgentResearchSystem`

## Important Notes

- Requires AppleScript permissions to access Notes.app
- API keys must be configured before running
- State is persisted to handle crash recovery
- Processed notes are tracked to avoid duplicate research within 1 hour
- All research results are automatically synced via iCloud