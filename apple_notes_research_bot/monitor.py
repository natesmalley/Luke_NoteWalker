"""
Apple Notes monitoring via AppleScript integration
"""

import asyncio
import subprocess
import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class Note:
    """Represents an Apple Note"""
    id: str
    name: str
    body: str
    folder: str
    creation_date: datetime
    modification_date: datetime
    content_hash: str = ""
    
    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate hash of note content for change detection"""
        content = f"{self.name}{self.body}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def has_changed(self, other: "Note") -> bool:
        """Check if note content has changed"""
        return self.content_hash != other.content_hash

class NotesMonitor:
    """Monitors Apple Notes for changes using AppleScript"""
    
    def __init__(self, folders: List[str] = None):
        self.folders = folders or ["Notes"]
        self.processed_notes: Dict[str, Note] = {}
        self.state_file = Path(".notes_monitor_state.json")
        self._load_state()
    
    def _load_state(self):
        """Load previously processed notes from state file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)
                    for note_id, note_data in state_data.items():
                        # Convert date strings back to datetime
                        note_data['creation_date'] = datetime.fromisoformat(note_data['creation_date'])
                        note_data['modification_date'] = datetime.fromisoformat(note_data['modification_date'])
                        self.processed_notes[note_id] = Note(**note_data)
                logger.info(f"Loaded {len(self.processed_notes)} notes from state")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
                self.processed_notes = {}
    
    def _save_state(self):
        """Save processed notes to state file"""
        try:
            state_data = {}
            for note_id, note in self.processed_notes.items():
                note_dict = asdict(note)
                # Convert datetime to ISO format strings
                note_dict['creation_date'] = note.creation_date.isoformat()
                note_dict['modification_date'] = note.modification_date.isoformat()
                state_data[note_id] = note_dict
            
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
            logger.debug(f"Saved {len(state_data)} notes to state")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    async def get_all_notes(self) -> List[Note]:
        """Retrieve all notes from specified folders"""
        notes = []
        
        for folder in self.folders:
            try:
                applescript = f'''
                tell application "Notes"
                    set notesList to {{}}
                    try
                        set targetFolder to folder "{folder}"
                    on error
                        -- If folder doesn't exist, use all notes
                        set targetFolder to every note
                    end try
                    
                    repeat with theNote in notes of targetFolder
                        try
                            set noteID to id of theNote as string
                            set noteName to name of theNote as string
                            set noteBody to body of theNote as string
                            set noteFolder to name of container of theNote as string
                        set noteCreation to creation date of theNote
                        set noteModification to modification date of theNote
                        
                            set noteRecord to "{{" & ¬
                                "\\"id\\": \\"" & noteID & "\\"," & ¬
                                "\\"name\\": \\"" & noteName & "\\"," & ¬
                                "\\"folder\\": \\"" & noteFolder & "\\"," & ¬
                                "\\"creation_date\\": \\"" & (noteCreation as string) & "\\"," & ¬
                                "\\"modification_date\\": \\"" & (noteModification as string) & "\\"" & ¬
                                "}}"
                            
                            set end of notesList to noteRecord
                        end try
                    end repeat
                    
                    return "[" & (my joinList(notesList, ",")) & "]"
                end tell

                on joinList(theList, theDelimiter)
                    set AppleScript's text item delimiters to theDelimiter
                    set theString to theList as string
                    set AppleScript's text item delimiters to ""
                    return theString
                end joinList
                '''
                
                result = await self._run_applescript(applescript)
                
                if result:
                    # Parse JSON response
                    notes_data = json.loads(result)
                    
                    for note_data in notes_data:
                        # Get full note body separately to avoid escaping issues
                        note_body = await self._get_note_body(note_data['id'])
                        
                        # Parse dates
                        creation_date = self._parse_applescript_date(note_data['creation_date'])
                        modification_date = self._parse_applescript_date(note_data['modification_date'])
                        
                        note = Note(
                            id=note_data['id'],
                            name=note_data['name'],
                            body=note_body or "",
                            folder=note_data['folder'],
                            creation_date=creation_date,
                            modification_date=modification_date
                        )
                        notes.append(note)
                
            except Exception as e:
                logger.error(f"Failed to get notes from folder '{folder}': {e}")
        
        return notes
    
    async def _get_note_body(self, note_id: str) -> Optional[str]:
        """Get the full body of a note by ID"""
        try:
            applescript = f'''
            tell application "Notes"
                set theNote to note id "{note_id}"
                return body of theNote as string
            end tell
            '''
            
            result = await self._run_applescript(applescript)
            return result
            
        except Exception as e:
            logger.error(f"Failed to get note body for {note_id}: {e}")
            return None
    
    async def _run_applescript(self, script: str) -> Optional[str]:
        """Execute AppleScript and return result"""
        try:
            process = await asyncio.create_subprocess_exec(
                'osascript', '-e', script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"AppleScript error: {stderr.decode()}")
                return None
            
            return stdout.decode().strip()
            
        except Exception as e:
            logger.error(f"Failed to run AppleScript: {e}")
            return None
    
    def _parse_applescript_date(self, date_str: str) -> datetime:
        """Parse AppleScript date format"""
        # AppleScript returns dates like "Monday, December 4, 2024 at 3:30:00 PM"
        try:
            # Try multiple formats
            formats = [
                "%A, %B %d, %Y at %I:%M:%S %p",
                "%A, %B %d, %Y at %H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # Fallback to current time if parsing fails
            logger.warning(f"Could not parse date: {date_str}")
            return datetime.now()
            
        except Exception as e:
            logger.error(f"Date parsing error: {e}")
            return datetime.now()
    
    async def check_for_changes(self) -> List[Note]:
        """Check for new or modified notes"""
        changed_notes = []
        
        try:
            current_notes = await self.get_all_notes()
            
            for note in current_notes:
                # Check if note is new or modified
                if note.id not in self.processed_notes:
                    logger.info(f"New note detected: {note.name}")
                    changed_notes.append(note)
                    self.processed_notes[note.id] = note
                    
                elif note.has_changed(self.processed_notes[note.id]):
                    logger.info(f"Modified note detected: {note.name}")
                    changed_notes.append(note)
                    self.processed_notes[note.id] = note
            
            # Save state if there were changes
            if changed_notes:
                self._save_state()
            
        except Exception as e:
            logger.error(f"Error checking for changes: {e}")
        
        return changed_notes
    
    async def update_note(self, note_id: str, new_content: str) -> bool:
        """Update a note's content"""
        try:
            # Escape the content for AppleScript
            escaped_content = new_content.replace('"', '\\"').replace('\n', '\\n')
            
            applescript = f'''
            tell application "Notes"
                set theNote to note id "{note_id}"
                set body of theNote to "{escaped_content}"
                return true
            end tell
            '''
            
            result = await self._run_applescript(applescript)
            
            if result:
                logger.info(f"Successfully updated note {note_id}")
                # Update our cached version
                if note_id in self.processed_notes:
                    self.processed_notes[note_id].body = new_content
                    self.processed_notes[note_id].content_hash = self.processed_notes[note_id].calculate_hash()
                    self.processed_notes[note_id].modification_date = datetime.now()
                    self._save_state()
                return True
            
        except Exception as e:
            logger.error(f"Failed to update note {note_id}: {e}")
        
        return False
    
    async def monitor_loop(self, check_interval: int = 30):
        """Continuous monitoring loop"""
        logger.info(f"Starting Notes monitor (checking every {check_interval} seconds)")
        
        while True:
            try:
                changed_notes = await self.check_for_changes()
                
                if changed_notes:
                    logger.info(f"Found {len(changed_notes)} changed notes")
                    yield changed_notes
                
                await asyncio.sleep(check_interval)
                
            except asyncio.CancelledError:
                logger.info("Monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(check_interval)