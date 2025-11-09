import json
import os
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path

from schema_generation.schema_generator import generate_schema


def download_from_s3(s3_uri: str, local_path: str) -> str:
    """
    Download a file from S3 to a local path.
    
    Args:
        s3_uri: S3 URI in format 's3://bucket/key'
        local_path: Local file path to save the file
    
    Returns:
        Local file path
    """
    try:
        import boto3
    except ImportError:
        raise ImportError(
            "boto3 is required for S3 support. "
            "Install it with: pip install boto3"
        )
    
    # Parse S3 URI
    if not s3_uri.startswith('s3://'):
        raise ValueError(f"Invalid S3 URI format: {s3_uri}. Expected format: s3://bucket/key")
    
    s3_uri = s3_uri[5:]  # Remove 's3://'
    parts = s3_uri.split('/', 1)
    
    if len(parts) != 2:
        raise ValueError(f"Invalid S3 URI format: s3://{s3_uri}. Expected: s3://bucket/key")
    
    bucket_name, key = parts
    
    # Download from S3
    s3_client = boto3.client('s3')
    s3_client.download_file(bucket_name, key, local_path)
    
    return local_path


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for schema generation.
    
    Event structure:
    {
        "file_path": "s3://bucket/file.csv" or "/path/to/file.csv",
        "sample_rows": 100,  // optional, default: 100
        "use_business_types": true,  // optional, default: true
        "file_type": "csv"  // optional, auto-detected if not provided
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": {
            "schema": { ... },
            "file_path": "...",
            "file_type": "csv|jsonl|parquet"
        }
    }
    
    Error response:
    {
        "statusCode": 400|500,
        "body": {
            "error": "Error message",
            "error_type": "ValueError|FileNotFoundError|..."
        }
    }
    """
    # Initialize response
    response_body: Dict[str, Any] = {}
    status_code = 200
    temp_file_path: Optional[str] = None
    
    try:
        # Extract parameters from event
        file_path = event.get('file_path')
        if not file_path:
            raise ValueError("Missing required parameter: file_path")
        
        sample_rows = event.get('sample_rows', 100)
        use_business_types = event.get('use_business_types', True)
        file_type = event.get('file_type')  # Optional
        
        # Validate sample_rows
        if not isinstance(sample_rows, int) or sample_rows < 1:
            raise ValueError("sample_rows must be a positive integer")
        
        # Validate use_business_types
        if not isinstance(use_business_types, bool):
            raise ValueError("use_business_types must be a boolean")
        
        # Handle S3 URIs
        if file_path.startswith('s3://'):
            # Create temporary file for S3 download
            temp_dir = tempfile.mkdtemp()
            # Extract filename from S3 key
            s3_key = file_path.split('/', 3)[-1] if '/' in file_path[5:] else 'file'
            file_name = os.path.basename(s3_key) or 'file'
            temp_file_path = os.path.join(temp_dir, file_name)
            
            # Download from S3
            download_from_s3(file_path, temp_file_path)
            local_file_path = temp_file_path
        else:
            # Local file path
            local_file_path = file_path
        
        # Generate schema
        schema = generate_schema(
            file_path=local_file_path,
            sample_rows=sample_rows,
            use_business_types=use_business_types,
            file_type=file_type
        )
        
        # Detect file type if not provided
        if file_type is None:
            from schema_generation.schema_generator import detect_file_type
            detected_type = detect_file_type(local_file_path)
        else:
            detected_type = file_type
        
        # Build response
        response_body = {
            "schema": schema,
            "file_path": file_path,
            "file_type": detected_type,
            "sample_rows": sample_rows,
            "use_business_types": use_business_types
        }
        
    except ValueError as e:
        status_code = 400
        response_body = {
            "error": str(e),
            "error_type": "ValueError"
        }
    
    except FileNotFoundError as e:
        status_code = 404
        response_body = {
            "error": str(e),
            "error_type": "FileNotFoundError"
        }
    
    except ImportError as e:
        status_code = 500
        response_body = {
            "error": str(e),
            "error_type": "ImportError"
        }
    
    except Exception as e:
        status_code = 500
        response_body = {
            "error": str(e),
            "error_type": type(e).__name__
        }
    
    finally:
        # Clean up temporary file if created
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                # Remove temp directory if empty
                temp_dir = os.path.dirname(temp_file_path)
                if os.path.exists(temp_dir):
                    try:
                        os.rmdir(temp_dir)
                    except OSError:
                        pass  # Directory not empty, leave it
            except OSError:
                pass  # Ignore cleanup errors
    
    # Return Lambda response
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(response_body)
    }

