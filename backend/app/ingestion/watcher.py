"""File system watcher"""

import asyncio
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

from app.ingestion.worker import IngestionWorker
from app.config import settings

logger = logging.getLogger(__name__)


class LogFileHandler(FileSystemEventHandler):
    """Handler for log file events"""
    
    def __init__(self, worker: IngestionWorker):
        self.worker = worker
        self.loop = asyncio.get_event_loop()
    
    def on_created(self, event):
        """Handle new file creation"""
        if event.is_directory:
            return
        
        logger.info(f"New file detected: {event.src_path}")
        asyncio.run_coroutine_threadsafe(
            self.worker.ingest_file(event.src_path, incremental=False),
            self.loop
        )
    
    def on_modified(self, event):
        """Handle file modification"""
        if event.is_directory:
            return
        
        logger.info(f"File modified: {event.src_path}")
        asyncio.run_coroutine_threadsafe(
            self.worker.ingest_file(event.src_path, incremental=True),
            self.loop
        )


class FileWatcher:
    """Watches a directory for log file changes"""
    
    def __init__(self, directory: str = None):
        self.directory = directory or settings.logs_directory
        self.worker = IngestionWorker()
        self.observer = Observer()
    
    async def start(self):
        """Start watching directory"""
        
        logger.info(f"Starting file watcher on: {self.directory}")
        
        # Ensure directory exists
        Path(self.directory).mkdir(parents=True, exist_ok=True)
        
        # Setup handler
        event_handler = LogFileHandler(self.worker)
        self.observer.schedule(event_handler, self.directory, recursive=True)
        
        # Start observer
        self.observer.start()
        logger.info("File watcher started")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
            logger.info("File watcher stopped")
        
        self.observer.join()
    
    def stop(self):
        """Stop watching"""
        self.observer.stop()
        self.observer.join()
