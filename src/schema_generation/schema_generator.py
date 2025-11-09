import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

from schema_generation.csv.csv_schema_generator import generate_csv_schema
from schema_generation.jsonl.jsonl_schema_generator import generate_jsonl_schema
from schema_generation.parquet.parquet_schema_generator import generate_parquet_schema


def detect_file_type(file_path: str) -> str:
    """
    Detect the file type based on extension and content.
    
    Args:
        file_path: Path to the file
    
    Returns:
        File type: 'csv', 'jsonl', 'parquet', or raises ValueError if unsupported
    
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file type cannot be determined or is unsupported
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get file extension
    path = Path(file_path)
    extension = path.suffix.lower()
    
    # Check by extension first
    if extension in ['.csv']:
        return 'csv'
    elif extension in ['.jsonl', '.jsonlines', '.ndjson']:
        return 'jsonl'
    elif extension in ['.parquet', '.parq']:
        return 'parquet'
    elif extension == '.gz':
        # Check if it's a compressed JSONL file
        if path.stem.lower().endswith(('.jsonl', '.jsonlines', '.ndjson')):
            return 'jsonl'
    
    # If extension is ambiguous or missing, try content-based detection
    try:
        # First check for Parquet magic bytes (binary format)
        with open(file_path, 'rb') as f:
            first_bytes = f.read(4)
            if first_bytes == b'PAR1':
                # Check end of file too
                try:
                    f.seek(-4, 2)  # Seek to 4 bytes from end
                    last_bytes = f.read(4)
                    if last_bytes == b'PAR1':
                        return 'parquet'
                except (IOError, OSError):
                    # File might be too small or have issues, but start looks like parquet
                    return 'parquet'
        
        # For text-based formats, read as text
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline().strip()
            
            if not first_line:
                raise ValueError(f"File appears to be empty: {file_path}")
            
            # Try to detect JSONL (first line should be valid JSON object)
            try:
                parsed = json.loads(first_line)
                if isinstance(parsed, dict):
                    # Check if there's a second line to confirm it's JSONL (not single JSON)
                    second_line = f.readline().strip()
                    if second_line:
                        # Has multiple lines, likely JSONL
                        return 'jsonl'
                    else:
                        # Single line JSON - could be JSONL with one object
                        return 'jsonl'
            except json.JSONDecodeError:
                pass
            
            # Try to detect CSV (looks for comma-separated values)
            if ',' in first_line:
                parts = first_line.split(',')
                if len(parts) > 1:
                    # Read second line to confirm it's CSV
                    second_line = f.readline().strip()
                    if second_line and ',' in second_line:
                        return 'csv'
                    # Even if no second line, if first line has multiple comma-separated parts, likely CSV
                    if len(parts) >= 2:
                        return 'csv'
    
    except (IOError, OSError, UnicodeDecodeError) as e:
        raise ValueError(f"Cannot read file to detect type: {e}")
    
    # If we can't determine the type
    raise ValueError(
        f"Cannot determine file type for: {file_path}. "
        f"Supported types: CSV (.csv), JSONL (.jsonl, .jsonlines, .ndjson), "
        f"Parquet (.parquet, .parq)"
    )


def generate_schema(
    file_path: str,
    sample_rows: int = 100,
    use_business_types: bool = True,
    file_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a JSON schema for a file by automatically detecting the file type.
    
    This is a unified interface that automatically detects the file type (CSV, JSONL, or Parquet)
    and generates the appropriate schema using the corresponding generator.
    
    Args:
        file_path: Path to the file (CSV, JSONL, or Parquet)
        sample_rows: Number of rows to sample for schema generation (default: 100)
        use_business_types: Whether to infer business types from sample data (default: True)
                           Note: CSV generator always uses business types
        file_type: Optional explicit file type ('csv', 'jsonl', 'parquet'). 
                   If None, will auto-detect from file extension and content.
    
    Returns:
        JSON schema dictionary with the following structure:
        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": { ... },
            "required": [ ... ],
            "metadata": { ... }  # For parquet and jsonl
        }
    
    Example:
        >>> from schema_generation.schema_generator import generate_schema
        >>> # Auto-detect file type
        >>> schema = generate_schema("data.csv")
        >>> schema = generate_schema("data.jsonl", sample_rows=50)
        >>> schema = generate_schema("data.parquet", use_business_types=False)
        >>> 
        >>> # Explicit file type
        >>> schema = generate_schema("data.txt", file_type="csv")
    
    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If file type cannot be determined or is unsupported
        ImportError: If pyarrow is required but not installed (for parquet files)
        json.JSONDecodeError: If JSONL file contains invalid JSON
    """
    # Detect file type if not provided
    if file_type is None:
        file_type = detect_file_type(file_path)
    else:
        file_type = file_type.lower()
        if file_type not in ['csv', 'jsonl', 'parquet']:
            raise ValueError(
                f"Unsupported file_type: {file_type}. "
                f"Supported types: 'csv', 'jsonl', 'parquet'"
            )
    
    # Route to appropriate generator
    if file_type == 'csv':
        # CSV generator doesn't have use_business_types parameter
        # It always uses business types
        return generate_csv_schema(file_path, sample_rows=sample_rows)
    
    elif file_type == 'jsonl':
        return generate_jsonl_schema(
            file_path,
            sample_rows=sample_rows,
            use_business_types=use_business_types
        )
    
    elif file_type == 'parquet':
        return generate_parquet_schema(
            file_path,
            sample_rows=sample_rows,
            use_business_types=use_business_types
        )
    
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

