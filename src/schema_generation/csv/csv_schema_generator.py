from typing import Dict, Any
from schema_generation.common.data_infer import infer_types


def generate_csv_schema(csv_file_path: str, sample_rows: int = 100) -> Dict[str, Any]:
    """Generate a JSON schema for a CSV file with both business_type and data_type"""
    import csv
    
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        headers = reader.fieldnames or []
        
        # Track both business types and data types
        column_business_types = {header: set() for header in headers}
        column_data_types = {header: set() for header in headers}
        
        row_count = 0
        for row in reader:
            if row_count >= sample_rows:
                break
            
            for header in headers:
                value = row.get(header, '')
                business_type, data_type = infer_types(value)
                
                if business_type:
                    column_business_types[header].add(business_type)
                column_data_types[header].add(data_type)
            
            row_count += 1
        
        # Build schema
        properties = {}
        required = []
        
        for header in headers:
            business_types = column_business_types[header]
            data_types = column_data_types[header]
            
            # Remove 'null' from data types for required check
            non_null_data_types = data_types - {'null'}
            
            if not non_null_data_types:
                # All nulls
                prop = {
                    "type": ["string", "null"],
                    "description": f"Column: {header}"
                }
            elif len(non_null_data_types) == 1:
                # Single data type
                data_type = list(non_null_data_types)[0]
                if 'null' in data_types:
                    prop = {
                        "type": [data_type, "null"],
                        "description": f"Column: {header}"
                    }
                else:
                    prop = {
                        "type": data_type,
                        "description": f"Column: {header}"
                    }
                    required.append(header)
            else:
                # Multiple data types
                type_list = list(non_null_data_types)
                if 'null' in data_types:
                    type_list.append('null')
                prop = {
                    "type": type_list,
                    "description": f"Column: {header}"
                }
            
            # Add business type if detected
            if business_types:
                # If multiple business types, use the most common one
                # Or you could use a list if multiple are detected
                business_type = list(business_types)[0] if len(business_types) == 1 else list(business_types)
                prop["business_type"] = business_type
            
            properties[header] = prop
        
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": properties,
            "required": required
        }
        
        return schema