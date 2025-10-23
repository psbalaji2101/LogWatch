"""ingestion worker"""

import asyncio
import logging
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
import uuid

from app.ingestion.parsers import (
    JSONParser, CSVParser, RegexParser, HeuristicParser
)
from app.ingestion.checkpoint import CheckpointManager
from app.search.client import get_opensearch_client, bulk_index_logs
from app.config import settings

logger = logging.getLogger(__name__)


class IngestionWorker:
    """log ingestion worker"""
    
    def __init__(self):
        self.checkpoint_manager = CheckpointManager()
        self.parsers = [
            JSONParser(),
            CSVParser(),
            RegexParser(),
            HeuristicParser()  # Fallback
        ]
        self.batch_size = settings.batch_size
        self.ingest_id = str(uuid.uuid4())
    
    async def ingest_file(self, file_path: str, incremental: bool = True):
        """Ingest a single log file"""
        
        logger.info(f"Ingesting file: {file_path}")
        
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return
        
        # Get checkpoint
        offset = 0
        if incremental:
            checkpoint_offset = self.checkpoint_manager.get_checkpoint(file_path)
            if checkpoint_offset:
                offset = checkpoint_offset
                logger.info(f"Resuming from offset {offset}")
        
        # Read file
        batch = []
        line_number = 0
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Seek to offset
            if offset > 0:
                f.seek(offset)
            
            # for line in f:
            #     line_number += 1
            #     line = line.strip()
                
            #     if not line:
            #         continue
                
            #     # Parse line
            #     parsed = self._parse_line(line)
                
            #     # Create document
            #     doc = {
            #         'timestamp': parsed['timestamp'].isoformat() if parsed['timestamp'] else datetime.utcnow().isoformat(),
            #         'source_file': file_path,
            #         'line_number': line_number,
            #         'raw_line': line,
            #         'tokens': parsed['tokens'],
            #         'fields': parsed['fields'],
            #         'ingest_id': self.ingest_id
            #     }
                
            #     batch.append(doc)
                
            #     # Bulk index when batch is full
            #     if len(batch) >= self.batch_size:
            #         self._flush_batch(batch)
            #         batch = []
                    
            #         # Update checkpoint
            #         current_offset = f.tell()
            #         last_modified = path.stat().st_mtime
            #         self.checkpoint_manager.set_checkpoint(file_path, current_offset, last_modified)
            

            while True:
                current_position = f.tell()  # Get position BEFORE reading
                line = f.readline()
                
                if not line:
                    break
                
                line_number += 1
                line = line.strip()
                
                if not line:
                    continue
                
                # Parse line
                parsed = self._parse_line(line)
                
                # Create document
                doc = {
                    'timestamp': parsed['timestamp'].isoformat() if parsed['timestamp'] else datetime.utcnow().isoformat(),
                    'source_file': file_path,
                    'line_number': line_number,
                    'raw_line': line,
                    'tokens': parsed['tokens'],
                    'fields': parsed['fields'],
                    'ingest_id': self.ingest_id
                }
                
                batch.append(doc)
                
                # Bulk index when batch is full
                if len(batch) >= self.batch_size:
                    self._flush_batch(batch)
                    batch = []
                    
                    # Update checkpoint with current position
                    last_modified = path.stat().st_mtime
                    self.checkpoint_manager.set_checkpoint(file_path, current_position, last_modified)



            # Flush remaining
            if batch:
                self._flush_batch(batch)
            
            # Final checkpoint
            final_offset = f.tell()
            last_modified = path.stat().st_mtime
            self.checkpoint_manager.set_checkpoint(file_path, final_offset, last_modified)
        
        logger.info(f"Completed ingestion: {file_path} ({line_number} lines)")
    
    def _parse_line(self, line: str) -> Dict[str, Any]:
        """Parse a log line using available parsers"""
        
        for parser in self.parsers:
            if parser.can_parse(line):
                try:
                    return parser.parse(line)
                except Exception as e:
                    logger.warning(f"Parser {parser.__class__.__name__} failed: {e}")
                    continue
        
        # Should never reach here (HeuristicParser always succeeds)
        return {
            'timestamp': datetime.utcnow(),
            'fields': {},
            'tokens': []
        }
    
    def _flush_batch(self, batch: List[Dict]):
        """Flush batch to OpenSearch"""
        
        if not batch:
            return
        
        try:
            client = get_opensearch_client()
            result = bulk_index_logs(client, batch)
            logger.info(f"Flushed batch: {result['success']} successful, {result['errors']} errors")
        except Exception as e:
            logger.error(f"Failed to flush batch: {e}")
            raise
