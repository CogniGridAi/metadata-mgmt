import json
from typing import Dict, Any, Optional
from datetime import datetime, date
from schema_generation.common.data_infer import infer_types


def _parquet_type_to_json_schema_type(parquet_type: str) -> str:
    """Convert Parquet type to JSON Schema type"""
    type_mapping = {
        'bool': 'boolean',
        'int8': 'integer',
        'int16': 'integer',
        'int32': 'integer',
        'int64': 'integer',
        'uint8': 'integer',
        'uint16': 'integer',
        'uint32': 'integer',
        'uint64': 'integer',
        'float32': 'number',
        'float64': 'number',
        'double': 'number',
        'string': 'string',
        'binary': 'string',
        'date32': 'date',
        'date64': 'date',
        'timestamp': 'datetime',
        'time32': 'time',
        'time64': 'time',
    }
    
    # Handle nullable types
    if parquet_type.startswith('null') or parquet_type == 'null':
        return 'null'
    
    # Extract base type if it's a complex type
    base_type = parquet_type.split('[')[0].split('(')[0].lower()
    
    return type_mapping.get(base_type, 'string')


def _convert_value_to_string(value: Any) -> str:
    """Convert a value to string for type inference"""
    if value is None:
        return ''
    if isinstance(value, (list, dict)):
        return json.dumps(value) if value else ''
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def generate_parquet_schema(
    parquet_file_path: str, 
    sample_rows: int = 100,
    use_business_types: bool = True
) -> Dict[str, Any]:
    """
    Generate a JSON schema for a Parquet file with both business_type and data_type.
    
    This function reads a Parquet file, extracts its schema, and generates a JSON Schema
    that includes both the Parquet data types and inferred business types (email, URL, etc.)
    from sample data.
    
    Args:
        parquet_file_path: Path to the Parquet file
        sample_rows: Number of rows to sample for business type inference (default: 100)
        use_business_types: Whether to infer business types from sample data (default: True)
    
    Returns:
        JSON schema dictionary with the following structure:
        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "column_name": {
                    "type": "string|integer|number|boolean|...",
                    "business_type": "email|url|phone_number|...",  # optional
                    "parquet_type": "string|int64|float64|...",
                    "nullable": true|false,
                    "description": "Column: column_name (Parquet type: ...)"
                }
            },
            "required": ["column1", "column2", ...],
            "metadata": {
                "num_rows": 1000,
                "num_columns": 5,
                "parquet_schema_version": "1.0"
            }
        }
    
    Example:
        >>> from schema_generation.parquet.parquet_schema_generator import generate_parquet_schema
        >>> schema = generate_parquet_schema("data.parquet", sample_rows=50)
        >>> print(schema["properties"]["email"]["business_type"])
        'email'
    
    Raises:
        ImportError: If pyarrow is not installed
        FileNotFoundError: If the parquet file does not exist
    """
    try:
        import pyarrow.parquet as pq
    except ImportError:
        raise ImportError(
            "pyarrow is required for parquet schema generation. "
            "Install it with: pip install pyarrow"
        )
    
    # Read parquet file
    parquet_file = pq.ParquetFile(parquet_file_path)
    parquet_schema = parquet_file.schema
    
    # Read sample data for business type inference
    table = parquet_file.read()
    df = table.to_pandas()
    
    # Limit sample rows
    sample_df = df.head(sample_rows) if len(df) > sample_rows else df
    
    # Track business types and data types for each column
    column_business_types = {}
    column_data_types = {}
    column_nullable = {}
    
    properties = {}
    required = []
    
    # Process each column
    for i, field in enumerate(parquet_schema):
        column_name = field.name
        parquet_type = str(field.type)
        is_nullable = field.nullable
        
        column_nullable[column_name] = is_nullable
        
        # Convert parquet type to JSON schema type
        json_type = _parquet_type_to_json_schema_type(parquet_type)
        
        # Initialize sets for this column
        column_business_types[column_name] = set()
        column_data_types[column_name] = set()
        
        # Sample values for business type inference
        if use_business_types and column_name in sample_df.columns:
            sample_values = sample_df[column_name].dropna().head(50)  # Sample up to 50 non-null values
            
            for value in sample_values:
                value_str = _convert_value_to_string(value)
                business_type, inferred_data_type = infer_types(value_str)
                
                if business_type:
                    column_business_types[column_name].add(business_type)
                column_data_types[column_name].add(inferred_data_type)
        
        # Build property schema
        # Use parquet type as primary, but allow inferred types if they differ
        inferred_types = column_data_types[column_name]
        
        # Determine the final type
        if not inferred_types or (len(inferred_types) == 1 and 'null' in inferred_types):
            # All nulls or no data
            if is_nullable:
                final_type = [json_type, 'null'] if json_type != 'null' else ['string', 'null']
            else:
                final_type = json_type if json_type != 'null' else 'string'
        elif len(inferred_types) == 1:
            # Single inferred type
            inferred_type = list(inferred_types)[0]
            if inferred_type != json_type and inferred_type != 'null':
                # Use inferred type if it's more specific
                final_type = inferred_type
            else:
                final_type = json_type
            
            if is_nullable:
                if isinstance(final_type, list):
                    if 'null' not in final_type:
                        final_type.append('null')
                else:
                    final_type = [final_type, 'null']
        else:
            # Multiple types detected
            non_null_types = inferred_types - {'null'}
            if non_null_types:
                type_list = list(non_null_types)
                # Prefer parquet type if it's in the list
                if json_type in type_list:
                    type_list = [json_type] + [t for t in type_list if t != json_type]
                else:
                    type_list.insert(0, json_type)
            else:
                type_list = [json_type]
            
            if is_nullable or 'null' in inferred_types:
                if 'null' not in type_list:
                    type_list.append('null')
            
            final_type = type_list if len(type_list) > 1 else (type_list[0] if type_list else json_type)
        
        # Build property
        prop = {
            "type": final_type,
            "description": f"Column: {column_name} (Parquet type: {parquet_type})"
        }
        
        # Add business type if detected
        if use_business_types and column_business_types[column_name]:
            business_types = column_business_types[column_name]
            if len(business_types) == 1:
                prop["business_type"] = list(business_types)[0]
            else:
                prop["business_type"] = list(business_types)
        
        # Add parquet metadata
        prop["parquet_type"] = parquet_type
        prop["nullable"] = is_nullable
        
        properties[column_name] = prop
        
        # Add to required if not nullable
        if not is_nullable:
            required.append(column_name)
    
    # Build final schema
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": properties,
        "required": required if required else []
    }
    
    # Add metadata about the parquet file
    schema["metadata"] = {
        "num_rows": len(df),
        "num_columns": len(parquet_schema),
        "parquet_schema_version": str(parquet_file.metadata.format_version) if hasattr(parquet_file.metadata, 'format_version') else None
    }
    
    return schema

