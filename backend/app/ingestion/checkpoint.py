"""Checkpoint manager for tracking file offsets"""

import sqlite3
import logging
import tempfile
from typing import Optional
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages file processing checkpoints"""
    
    # def __init__(self, db_path: Optional[str] = None):
    #     self.db_path = db_path or settings.checkpoint_db
    #     self._ensure_db()
    
    def __init__(self, db_path: Optional[str] = None):
        db_path = Path(db_path or settings.checkpoint_db)

        # If absolute path is not writable (like /data), fallback to temp dir
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            db_path = Path(tempfile.gettempdir()) / db_path.name

        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Create checkpoint database if it doesn't exist"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                file_path TEXT PRIMARY KEY,
                offset INTEGER NOT NULL,
                last_modified REAL NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_checkpoint(self, file_path: str) -> Optional[int]:
        """Get last processed offset for a file"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT offset FROM checkpoints WHERE file_path = ?",
            (file_path,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def set_checkpoint(self, file_path: str, offset: int, last_modified: float):
        """Save checkpoint for a file"""
        # SQLite INTEGER max value (64-bit signed)
        MAX_SQLITE_INT = 9223372036854775807
        
        # Validate and clamp offset to prevent overflow
        if offset > MAX_SQLITE_INT:
            logger.warning(f"Offset {offset} exceeds SQLite max, clamping to {MAX_SQLITE_INT}")
            offset = MAX_SQLITE_INT
        
        # Ensure offset is non-negative
        if offset < 0:
            logger.warning(f"Negative offset {offset} detected, setting to 0")
            offset = 0
        
        # Convert last_modified to float and ensure it's reasonable
        # If it looks like nanoseconds (> 10^12), convert to seconds
        if last_modified > 1e12:
            logger.warning(f"last_modified {last_modified} looks like nanoseconds, converting to seconds")
            last_modified = last_modified / 1e9
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO checkpoints (file_path, offset, last_modified, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (file_path, int(offset), float(last_modified)))
            
            conn.commit()
            logger.debug(f"Checkpoint saved: {file_path} @ {offset}")
        except (OverflowError, sqlite3.IntegrityError) as e:
            logger.error(f"Failed to save checkpoint for {file_path}: {e}")
            logger.error(f"Values: offset={offset} (type={type(offset)}), last_modified={last_modified} (type={type(last_modified)})")
            raise
        finally:
            conn.close()
    
    def clear_checkpoint(self, file_path: str):
        """Clear checkpoint for a file"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM checkpoints WHERE file_path = ?", (file_path,))
        
        conn.commit()
        conn.close()
