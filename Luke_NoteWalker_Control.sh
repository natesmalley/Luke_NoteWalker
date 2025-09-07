#!/bin/bash

# Luke_NoteWalker Control Script
# Manages the Apple Notes Research Bot with graceful shutdown and restart

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"
BOT_MODULE="apple_notes_research_bot"
PROCESS_NAME="Luke_NoteWalker"
LOG_FILE="$SCRIPT_DIR/luke_notewalker.log"

# Function to check if Luke_NoteWalker is running
check_running() {
    pgrep -f "python.*$BOT_MODULE" > /dev/null
    return $?
}

# Function to get Luke_NoteWalker process IDs
get_pids() {
    pgrep -f "python.*$BOT_MODULE"
}

# Function to gracefully stop Luke_NoteWalker
stop_luke_notewalker() {
    echo "🛑 Stopping Luke_NoteWalker..."
    
    if check_running; then
        local pids=$(get_pids)
        echo "Found running processes: $pids"
        
        # Send SIGTERM for graceful shutdown
        echo "$pids" | xargs kill -TERM 2>/dev/null
        
        # Wait up to 10 seconds for graceful shutdown
        local count=0
        while [ $count -lt 10 ] && check_running; do
            sleep 1
            count=$((count + 1))
            echo -n "."
        done
        
        # Force kill if still running
        if check_running; then
            echo -e "\n⚠️  Forcing shutdown..."
            echo "$pids" | xargs kill -9 2>/dev/null
            sleep 2
        fi
        
        if check_running; then
            echo "❌ Failed to stop Luke_NoteWalker"
            return 1
        else
            echo -e "\n✅ Luke_NoteWalker stopped successfully"
            return 0
        fi
    else
        echo "ℹ️  Luke_NoteWalker is not running"
        return 0
    fi
}

# Function to start Luke_NoteWalker
start_luke_notewalker() {
    echo "🚀 Starting Luke_NoteWalker..."
    
    # Check if virtual environment exists
    if [ ! -f "$VENV_PYTHON" ]; then
        echo "❌ Virtual environment not found at $VENV_PYTHON"
        echo "Please run: python3 -m venv venv && pip install -r apple_notes_research_bot/requirements.txt"
        exit 1
    fi
    
    # Load environment variables if .env exists
    if [ -f "$SCRIPT_DIR/.env" ]; then
        export $(cat "$SCRIPT_DIR/.env" | grep -v '^#' | xargs)
        echo "✅ Loaded environment variables from .env"
    else
        echo "⚠️  No .env file found - make sure API keys are set in environment"
    fi
    
    # Check for required API keys
    if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_anthropic_api_key_here" ]; then
        echo "❌ ANTHROPIC_API_KEY not configured properly"
        exit 1
    fi
    
    if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
        echo "❌ OPENAI_API_KEY not configured properly"
        exit 1
    fi
    
    # Start Luke_NoteWalker in background
    cd "$SCRIPT_DIR"
    nohup "$VENV_PYTHON" -m "$BOT_MODULE" > "$LOG_FILE" 2>&1 &
    local pid=$!
    
    # Wait a moment and check if it started successfully
    sleep 3
    if kill -0 $pid 2>/dev/null; then
        echo "✅ Luke_NoteWalker started successfully (PID: $pid)"
        echo "📁 Monitoring: Self Learning folder"
        echo "📝 Log file: $LOG_FILE"
        echo "🔍 Check status with: tail -f $LOG_FILE"
        return 0
    else
        echo "❌ Failed to start Luke_NoteWalker"
        echo "📝 Check log file: $LOG_FILE"
        return 1
    fi
}

# Function to show status
show_status() {
    echo "📊 Luke_NoteWalker Status:"
    echo "========================"
    
    if check_running; then
        local pids=$(get_pids)
        local pid_count=$(echo "$pids" | wc -w)
        echo "🟢 Status: Running ($pid_count process(es))"
        echo "🆔 PIDs: $pids"
        
        # Show recent log entries
        if [ -f "$LOG_FILE" ]; then
            echo "📝 Recent activity:"
            tail -5 "$LOG_FILE" | sed 's/^/   /'
        fi
    else
        echo "🔴 Status: Not running"
    fi
    
    echo "📂 Project directory: $SCRIPT_DIR"
    echo "🐍 Python executable: $VENV_PYTHON"
    echo "📁 Monitoring folder: Self Learning"
    echo "📝 Log file: $LOG_FILE"
}

# Function to restart Luke_NoteWalker
restart_luke_notewalker() {
    echo "🔄 Restarting Luke_NoteWalker..."
    echo "================================"
    
    stop_luke_notewalker
    sleep 2
    start_luke_notewalker
}

# Main script logic
case "${1:-restart}" in
    "start")
        if check_running; then
            echo "⚠️  Luke_NoteWalker is already running"
            show_status
        else
            start_luke_notewalker
        fi
        ;;
    "stop")
        stop_luke_notewalker
        ;;
    "restart")
        restart_luke_notewalker
        ;;
    "status")
        show_status
        ;;
    "logs")
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        else
            echo "📝 No log file found at: $LOG_FILE"
        fi
        ;;
    *)
        echo "🪸 Luke_NoteWalker Control Panel"
        echo "==============================="
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  start    - Start Luke_NoteWalker if not running"
        echo "  stop     - Gracefully stop Luke_NoteWalker"
        echo "  restart  - Stop and start Luke_NoteWalker (default)"
        echo "  status   - Show current status and recent activity"
        echo "  logs     - Follow real-time log output"
        echo ""
        echo "Double-click this file to restart Luke_NoteWalker"
        ;;
esac

# Keep terminal open if double-clicked
if [ -t 0 ]; then
    echo ""
    echo "Press any key to continue..."
    read -n 1
fi