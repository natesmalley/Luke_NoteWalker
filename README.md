# 🪸 Apple Notes Research Bot

An AI-powered research assistant that monitors Apple Notes and automatically conducts comprehensive research on new or changed notes using Claude and OpenAI.

## Features

- 🔍 **Real-time Monitoring**: Monitors Apple Notes folders for changes every 30 seconds
- 🤖 **AI-Powered Analysis**: Uses Claude to analyze notes and determine research needs (0.7 confidence threshold)
- 🔬 **Multi-Provider Research**: Parallel research using both Claude and OpenAI for comprehensive results
- 📝 **Professional Formatting**: Automatically formats research results with structured output
- ☁️ **iCloud Sync**: Seamless synchronization across all Apple devices
- 🔄 **Crash Recovery**: Persistent state management for reliability

## Prerequisites

- macOS 10.14 or later (required for Apple Notes integration)
- Python 3.8 or later
- Active API keys for:
  - [Anthropic Claude](https://console.anthropic.com/)
  - [OpenAI](https://platform.openai.com/api-keys)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Luke_NoteWalker
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r apple_notes_research_bot/requirements.txt
```

4. Configure API keys:
```bash
cp .env.template .env
# Edit .env and add your API keys
```

## Usage

### Quick Start
```bash
./start_bot.sh
```

### Manual Start
```bash
source venv/bin/activate
python -m apple_notes_research_bot
```

The bot will:
1. Monitor your Apple Notes for changes
2. Analyze new/modified notes for research opportunities
3. Conduct multi-source research when confidence > 0.7
4. Update notes with formatted research results
5. Sync changes via iCloud to all devices

## Configuration

Edit `.env` or set environment variables:

- `ANTHROPIC_API_KEY`: Your Claude API key (required)
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `RESEARCH_CONFIDENCE_THRESHOLD`: Minimum confidence for research (default: 0.7)
- `CHECK_INTERVAL`: Seconds between checks (default: 30)
- `LOG_LEVEL`: Logging verbosity (default: INFO)

## Supported Research Categories

- **Software Development**: APIs, frameworks, technical implementation
- **AI/ML**: Machine learning, models, data science
- **Building/Construction**: DIY projects, materials, tools
- **Lifestyle**: Activities, entertainment, travel, food
- **Productivity**: Workflow optimization, time management
- **General**: Information queries and research topics

## Security

- API keys are stored in environment variables or macOS keychain
- Never commit `.env` files to version control
- Use `.env.template` as a reference for required variables
- All sensitive files are properly gitignored

## Project Structure

```
Luke_NoteWalker/
├── apple_notes_research_bot/       # Main application code
│   ├── main.py                    # Entry point and orchestration
│   ├── monitor.py                 # Apple Notes monitoring via AppleScript
│   ├── analyzer.py                # AI-powered content analysis
│   ├── research_engine.py         # Multi-provider research execution
│   ├── formatter.py               # Research output formatting
│   ├── config.py                  # Configuration management
│   └── utils.py                   # Utilities and helpers
├── docs/                          # Technical documentation
│   └── architecture/              # System architecture docs
├── .env.template                  # Environment variables template
├── start_bot.sh                   # Quick start script
└── README.md                      # This file
```

## Troubleshooting

### AppleScript Permissions
If you see AppleScript errors, grant Terminal/IDE permission to control Notes:
1. System Preferences → Security & Privacy → Privacy → Automation
2. Enable your Terminal/IDE for Notes.app

### API Key Issues
- Ensure keys are properly set in `.env` file
- Check keys are valid and have sufficient credits
- Verify no extra spaces or quotes around keys

### Notes Not Updating
- Check Apple Notes is running
- Verify iCloud sync is enabled
- Ensure note is in monitored folder (default: "Notes")

## License

Proprietary - CoralCollective

## Support

For issues or questions, please contact the development team.