import json
from typing import Dict, Any, Set, Optional, List
from schema_generation.common.data_infer import infer_types


def _python_type_to_json_schema_type(value: Any) -> str:
    """Convert Python type to JSON Schema type"""
    if value is None:
        return 'null'
    elif isinstance(value, bool):
        return 'boolean'
    elif isinstance(value, int):
        return 'integer'
    elif isinstance(value, float):
        return 'number'
    elif isinstance(value, str):
        return 'string'
    elif isinstance(value, list):
        return 'array'
    elif isinstance(value, dict):
        return 'object'
    else:
        return 'string'


def _process_nested_object(
    obj: Dict[str, Any],
    path: str = "",
    sample_rows: int = 100,
    use_business_types: bool = True
) -> Dict[str, Any]:
    """
    Process a nested object and generate schema for it.
    
    Args:
        obj: The object to process
        path: Current path in the object (for nested keys)
        sample_rows: Number of samples to consider
        use_business_types: Whether to infer business types
    
    Returns:
        Schema properties dictionary
    """
    properties = {}
    
    for key, value in obj.items():
        full_path = f"{path}.{key}" if path else key
        
        if value is None:
            prop = {
                "type": "null",
                "description": f"Field: {full_path}"
            }
        elif isinstance(value, dict):
            # Nested object - recursively process
            nested_props = _process_nested_object(value, full_path, sample_rows, use_business_types)
            prop = {
                "type": "object",
                "properties": nested_props,
                "description": f"Field: {full_path} (nested object)"
            }
        elif isinstance(value, list):
            # Array - analyze items
            if value:
                # Analyze first few items to determine array item type
                item_types = set()
                item_business_types = set()
                
                for item in value[:min(10, len(value))]:  # Sample up to 10 items
                    item_type = _python_type_to_json_schema_type(item)
                    item_types.add(item_type)
                    
                    if use_business_types:
                        item_str = json.dumps(item) if isinstance(item, (dict, list)) else str(item)
                        business_type, inferred_type = infer_types(item_str)
                        if business_type:
                            item_business_types.add(business_type)
                        item_types.add(inferred_type)
                
                # Build array item schema
                if len(item_types) == 1:
                    item_type = list(item_types)[0]
                    if item_type == 'object' and value and isinstance(value[0], dict):
                        # Array of objects - process nested
                        nested_props = _process_nested_object(value[0], f"{full_path}[]", sample_rows, use_business_types)
                        items_schema = {
                            "type": "object",
                            "properties": nested_props
                        }
                    else:
                        items_schema = {"type": item_type}
                else:
                    # Multiple types in array
                    type_list = list(item_types - {'null'})
                    if 'null' in item_types:
                        type_list.append('null')
                    items_schema = {"type": type_list if len(type_list) > 1 else type_list[0]}
                
                prop = {
                    "type": "array",
                    "items": items_schema,
                    "description": f"Field: {full_path} (array)"
                }
                
                if use_business_types and item_business_types:
                    if len(item_business_types) == 1:
                        prop["items"]["business_type"] = list(item_business_types)[0]
                    else:
                        prop["items"]["business_type"] = list(item_business_types)
            else:
                # Empty array - default to array of any
                prop = {
                    "type": "array",
                    "items": {},
                    "description": f"Field: {full_path} (empty array)"
                }
        else:
            # Primitive type
            json_type = _python_type_to_json_schema_type(value)
            prop = {
                "type": json_type,
                "description": f"Field: {full_path}"
            }
            
            if use_business_types:
                value_str = str(value)
                business_type, inferred_type = infer_types(value_str)
                if business_type:
                    prop["business_type"] = business_type
                # Update type if inferred type is more specific
                if inferred_type != json_type and inferred_type != 'null':
                    prop["type"] = inferred_type
        
        properties[key] = prop
    
    return properties


def _merge_properties(
    properties_list: List[Dict[str, Any]],
    use_business_types: bool = True
) -> Dict[str, Any]:
    """
    Merge multiple property dictionaries from different JSON objects.
    
    Args:
        properties_list: List of property dictionaries to merge
        use_business_types: Whether business types were used
    
    Returns:
        Merged properties dictionary
    """
    if not properties_list:
        return {}
    
    # Start with first properties dict
    merged = {}
    for prop_dict in properties_list:
        for key, value in prop_dict.items():
            if key not in merged:
                # New key - add it
                merged[key] = value.copy() if isinstance(value, dict) else value
            else:
                # Existing key - merge types
                existing = merged[key]
                
                # Handle nested objects
                if existing.get("type") == "object" and value.get("type") == "object":
                    # Recursively merge nested objects
                    existing_props = existing.get("properties", {})
                    value_props = value.get("properties", {})
                    merged_props = _merge_properties([existing_props, value_props], use_business_types)
                    existing["properties"] = merged_props
                
                # Handle arrays
                elif existing.get("type") == "array" and value.get("type") == "array":
                    existing_items = existing.get("items", {})
                    value_items = value.get("items", {})
                    
                    # Merge array item types
                    existing_item_type = existing_items.get("type")
                    value_item_type = value_items.get("type")
                    
                    if existing_item_type and value_item_type:
                        if existing_item_type != value_item_type:
                            if isinstance(existing_item_type, list):
                                if value_item_type not in existing_item_type:
                                    existing_item_type.append(value_item_type)
                            elif isinstance(value_item_type, list):
                                if existing_item_type not in value_item_type:
                                    value_item_type.append(existing_item_type)
                                    existing_items["type"] = value_item_type
                            else:
                                existing_items["type"] = [existing_item_type, value_item_type]
                    
                    # Merge nested object properties in array items
                    if existing_items.get("type") == "object" and value_items.get("type") == "object":
                        existing_item_props = existing_items.get("properties", {})
                        value_item_props = value_items.get("properties", {})
                        merged_item_props = _merge_properties([existing_item_props, value_item_props], use_business_types)
                        existing_items["properties"] = merged_item_props
                    
                    existing["items"] = existing_items
                
                # Handle type merging for primitives
                else:
                    existing_type = existing.get("type")
                    value_type = value.get("type")
                    
                    if existing_type != value_type:
                        if isinstance(existing_type, list):
                            if value_type not in existing_type:
                                existing_type.append(value_type)
                        elif isinstance(value_type, list):
                            if existing_type not in value_type:
                                value_type.append(existing_type)
                                existing["type"] = value_type
                        else:
                            existing["type"] = [existing_type, value_type]
                    
                    # Merge business types
                    if use_business_types:
                        existing_business_type = existing.get("business_type")
                        value_business_type = value.get("business_type")
                        
                        if existing_business_type != value_business_type:
                            if isinstance(existing_business_type, list):
                                if value_business_type and value_business_type not in existing_business_type:
                                    existing_business_type.append(value_business_type)
                            elif isinstance(value_business_type, list):
                                if existing_business_type and existing_business_type not in value_business_type:
                                    value_business_type.append(existing_business_type)
                                    existing["business_type"] = value_business_type
                            elif existing_business_type and value_business_type:
                                existing["business_type"] = [existing_business_type, value_business_type]
                            elif value_business_type:
                                existing["business_type"] = value_business_type
    
    return merged


def generate_jsonl_schema(
    jsonl_file_path: str,
    sample_rows: int = 100,
    use_business_types: bool = True
) -> Dict[str, Any]:
    """
    Generate a JSON schema for a JSONL (JSON Lines) file with both business_type and data_type.
    
    This function reads a JSONL file (one JSON object per line), analyzes the structure,
    and generates a JSON Schema that includes both data types and inferred business types
    (email, URL, etc.) from sample data. Supports nested objects and arrays.
    
    Args:
        jsonl_file_path: Path to the JSONL file
        sample_rows: Number of lines to sample for schema generation (default: 100)
        use_business_types: Whether to infer business types from sample data (default: True)
    
    Returns:
        JSON schema dictionary with the following structure:
        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "field_name": {
                    "type": "string|integer|number|boolean|object|array|...",
                    "business_type": "email|url|phone_number|...",  # optional
                    "description": "Field: field_name"
                },
                "nested_object": {
                    "type": "object",
                    "properties": { ... }  # nested structure
                },
                "array_field": {
                    "type": "array",
                    "items": { "type": "string", ... }  # array item schema
                }
            },
            "required": ["field1", "field2", ...]
        }
    
    Example:
        >>> from schema_generation.jsonl.jsonl_schema_generator import generate_jsonl_schema
        >>> schema = generate_jsonl_schema("data.jsonl", sample_rows=50)
        >>> print(schema["properties"]["email"]["business_type"])
        'email'
    
    Raises:
        FileNotFoundError: If the JSONL file does not exist
        json.JSONDecodeError: If a line contains invalid JSON
    """
    # Track all fields across all objects
    all_field_types: Dict[str, Set[str]] = {}
    all_business_types: Dict[str, Set[str]] = {}
    all_field_presence: Dict[str, int] = {}  # Count how many objects have this field
    object_schemas: List[Dict[str, Any]] = []
    total_rows = 0
    
    try:
        with open(jsonl_file_path, 'r', encoding='utf-8') as f:
            row_count = 0
            for line in f:
                if row_count >= sample_rows:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    obj = json.loads(line)
                    total_rows += 1
                    
                    if not isinstance(obj, dict):
                        # Skip non-object lines
                        continue
                    
                    # Process this object to get its schema
                    obj_schema = _process_nested_object(obj, "", sample_rows, use_business_types)
                    object_schemas.append(obj_schema)
                    
                    # Track field presence
                    def track_fields(d: Dict[str, Any], prefix: str = ""):
                        for key, value in d.items():
                            full_key = f"{prefix}.{key}" if prefix else key
                            all_field_presence[full_key] = all_field_presence.get(full_key, 0) + 1
                            
                            if isinstance(value, dict):
                                track_fields(value, full_key)
                            elif isinstance(value, list) and value and isinstance(value[0], dict):
                                track_fields(value[0], f"{full_key}[]")
                    
                    track_fields(obj)
                    
                    row_count += 1
                    
                except json.JSONDecodeError as e:
                    # Skip invalid JSON lines
                    continue
    
    except FileNotFoundError:
        raise FileNotFoundError(f"JSONL file not found: {jsonl_file_path}")
    
    if not object_schemas:
        # Empty file or no valid objects
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {},
            "required": []
        }
    
    # Merge all object schemas
    merged_properties = _merge_properties(object_schemas, use_business_types)
    
    # Determine required fields (present in all objects)
    required = []
    for field, count in all_field_presence.items():
        if count == total_rows:
            # Field is present in all rows - check if it's a top-level field
            if '.' not in field:
                required.append(field)
    
    # Build final schema
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": merged_properties,
        "required": required if required else []
    }
    
    # Add metadata
    schema["metadata"] = {
        "num_rows": total_rows,
        "num_fields": len(merged_properties),
        "file_type": "jsonl"
    }
    
    return schema

