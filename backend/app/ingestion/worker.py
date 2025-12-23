"""Fixed ingestion worker - handles STRING timestamps"""

import asyncio
import logging
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
import uuid
import json

from app.ingestion.parsers import (
    JSONParser, CSVParser, RegexParser, HeuristicParser, ISO8601Parser, OTLPParser
)
from app.ingestion.timestamp_extractor import extract_timestamp
from app.ingestion.timestamp_parser import parse_timestamp, TimestampParseResult
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
            ISO8601Parser(),
            CSVParser(),
            RegexParser(),
            OTLPParser(),
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
                # FIXED: timestamp is now STRING, not datetime
                timestamp = parsed['timestamp'] if parsed['timestamp'] else datetime.utcnow().isoformat()
                
                doc = {
                    'timestamp': timestamp,  # STRING - no .isoformat() call
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
        # Phase A — lossless extraction of raw timestamp substring
        raw_ts = extract_timestamp(line)

        parser_result = None
        for parser in self.parsers:
            if parser.can_parse(line):
                try:
                    parser_result = parser.parse(line)
                    break
                except Exception as e:
                    logger.warning(f"Parser {parser.__class__.__name__} failed: {e}")
                    continue

        # If no parser returned a result, fallback to heuristic parser (should exist)
        if not parser_result:
            logger.debug("No parser matched line; using HeuristicParser fallback")
            parser_result = HeuristicParser().parse(line)

        # parser_result is expected to contain 'timestamp', 'fields', 'tokens'
        parser_ts = parser_result.get('timestamp') if isinstance(parser_result, dict) else None
        if isinstance(parser_ts, datetime):
            parser_dt = parser_ts
        else:
            parser_dt = None

        # Phase B — normalization + scoring
        norm = parse_timestamp(raw_ts, parser_dt)

        ingested_at = datetime.utcnow().replace(tzinfo=timezone.utc)

        # Decide canonical @timestamp based on confidence threshold
        threshold = 0.7
        timestamp_source = norm.source
        assumed_year = norm.assumed_year
        timezone_assumed = norm.timezone_assumed

        if norm.parsed_datetime and norm.confidence >= threshold:
            at_timestamp = norm.parsed_datetime.isoformat()
            parse_error = None
            timestamp_origin = 'normalized'
        else:
            # Explicit fallback to ingestion time; record failure metadata
            at_timestamp = ingested_at.isoformat()
            parse_error = norm.error or 'low_confidence'
            timestamp_origin = 'ingested_fallback'

        # Keep legacy 'timestamp' field for backward compatibility (string)
        legacy_timestamp = at_timestamp

        # Build normalized document (keeps existing fields)
        return {
            'timestamp': legacy_timestamp,
            '@timestamp': at_timestamp,
            'raw_timestamp': raw_ts,
            'ingested_at': ingested_at.isoformat(),
            'timestamp_confidence': float(norm.confidence),
            'timestamp_format': norm.format,
            'timestamp_source': timestamp_source,
            'timestamp_origin': timestamp_origin,
            'timestamp_assumed_year': assumed_year,
            'timestamp_timezone_assumed': timezone_assumed,
            'timestamp_parse_error': parse_error,
            'fields': parser_result.get('fields', {}),
            'tokens': parser_result.get('tokens', [])
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
            # Do not crash the whole ingestion run for transient indexing failures.
            # Persist failed batch to disk for later inspection and reprocessing.
            try:
                failed_dir = Path(settings.checkpoint_db).parent / "failed_batches"
                failed_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
                filename = failed_dir / f"failed_batch_{ts}.ndjson"
                with open(filename, 'w', encoding='utf-8') as fh:
                    for doc in batch:
                        fh.write(json.dumps(doc, default=str) + "\n")
                logger.error(f"Failed to flush batch: {e}. Persisted {len(batch)} logs to {filename}")
            except Exception as ex2:
                logger.error(f"Failed to persist failed batch: {ex2}")
            # Do NOT crash ingestion on transient indexing errors; continue processing.
            return
