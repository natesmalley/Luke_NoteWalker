# 🪸 Luke_NoteWalker Control System

Easy management for your Apple Notes AI Research Bot.

## 🖱️ Quick Desktop Control

**Double-click the desktop shortcut:**
- `Luke_NoteWalker.command` on your Desktop
- Automatically restarts Luke_NoteWalker with latest configuration
- Shows management options and status

## 🛠️ Manual Control Options

### Control Script Commands:
```bash
./Luke_NoteWalker_Control.sh [command]
```

**Available Commands:**
- `restart` - Stop and start Luke_NoteWalker (default action)
- `start` - Start Luke_NoteWalker if not running  
- `stop` - Gracefully stop Luke_NoteWalker
- `status` - Show current status and recent activity
- `logs` - Follow real-time log output

### Examples:
```bash
# Check if running
./Luke_NoteWalker_Control.sh status

# View live logs
./Luke_NoteWalker_Control.sh logs

# Stop the bot
./Luke_NoteWalker_Control.sh stop

# Start the bot
./Luke_NoteWalker_Control.sh start
```

## 🔧 What It Does

**Smart Process Management:**
- ✅ Checks for running instances
- ✅ Graceful shutdown with SIGTERM (10 second timeout)
- ✅ Force kill if needed (SIGKILL)
- ✅ Validates environment and API keys
- ✅ Starts in background with logging
- ✅ Shows process status and recent activity

**Safe Operation:**
- Won't start duplicate instances
- Loads API keys from `.env` file
- Validates configuration before starting
- Comprehensive error handling and feedback

## 📊 Status Information

When you check status, you'll see:
- 🟢/🔴 Running status
- 🆔 Process IDs
- 📝 Recent log activity
- 📁 Monitoring folder (Self Learning)
- 🐍 Python environment path

## 📝 Log Files

- **Location**: `luke_notewalker.log`
- **Content**: All bot activity, research results, errors
- **Viewing**: Use `logs` command for real-time monitoring

## 🚨 Troubleshooting

**If Luke_NoteWalker won't start:**
1. Check API keys are set in `.env` file
2. Verify virtual environment: `./venv/bin/python --version`
3. Check dependencies: `./venv/bin/pip list`
4. Review log file for errors

**If it shows multiple processes:**
- This is normal (parent/child processes)
- The control script handles both gracefully

## 🎯 Perfect For

- **Quick restarts** after configuration changes
- **Status monitoring** to ensure bot is running
- **Log monitoring** to see research activity
- **Clean shutdowns** before system maintenance
- **Desktop convenience** with double-click operation