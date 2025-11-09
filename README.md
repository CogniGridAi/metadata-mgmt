# Schema Generation Library

A Python library for automatically generating JSON schemas from CSV, JSONL, and Parquet files with intelligent type inference and business type detection.

## Features

- **Automatic file type detection** - Detects CSV, JSONL, and Parquet files by extension and content
- **Type inference** - Automatically infers data types (string, integer, float, boolean, date, etc.)
- **Business type detection** - Identifies semantic types (email, URL, phone number, UUID, etc.)
- **Nested structure support** - Handles nested objects and arrays in JSONL files
- **Unified interface** - Single function works with all supported file types

## Installation

### Prerequisites

- Python 3.8 or higher

### Install Dependencies

For basic usage (CSV and JSONL only):
```bash
# No dependencies needed - uses Python standard library
```

For Parquet support:
```bash
pip install -r requirements.txt
```

For development and testing:
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

## Quick Start

```python
from schema_generation import generate_schema

# Auto-detect file type and generate schema
schema = generate_schema("data.csv")
print(schema)
```

## Usage

### Basic Usage

The `generate_schema()` function automatically detects the file type and generates a schema:

```python
from schema_generation import generate_schema

# CSV file
schema = generate_schema("data.csv")

# JSONL file
schema = generate_schema("data.jsonl")

# Parquet file
schema = generate_schema("data.parquet")
```

### Parameters

```python
generate_schema(
    file_path: str,
    sample_rows: int = 100,
    use_business_types: bool = True,
    file_type: Optional[str] = None
) -> Dict[str, Any]
```

**Parameters:**

- `file_path` (str, required): Path to the file (CSV, JSONL, or Parquet)
- `sample_rows` (int, optional): Number of rows to sample for schema generation. Default: 100
- `use_business_types` (bool, optional): Whether to infer business types (email, URL, etc.). Default: True
  - Note: CSV generator always uses business types
- `file_type` (str, optional): Explicit file type ('csv', 'jsonl', 'parquet'). If None, auto-detects from extension and content

**Returns:**

A JSON schema dictionary with the following structure:

```json
{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "column_name": {
            "type": "string|integer|number|boolean|...",
            "business_type": "email|url|phone_number|...",  // optional
            "description": "Column: column_name",
            // For Parquet files:
            "parquet_type": "string|int64|float64|...",
            "nullable": true|false
        }
    },
    "required": ["column1", "column2", ...],
    "metadata": {  // For Parquet and JSONL
        "num_rows": 1000,
        "num_columns": 5,
        "file_type": "jsonl"  // or "parquet"
    }
}
```

### Examples

#### CSV Files

```python
from schema_generation import generate_schema

# Generate schema from CSV
schema = generate_schema("users.csv")

# With custom sampling
schema = generate_schema("users.csv", sample_rows=50)

# Example output
print(schema["properties"]["email"]["business_type"])  # 'email'
print(schema["properties"]["age"]["type"])  # 'integer'
```

**CSV Example:**
```csv
name,age,email,is_active
John Doe,30,john@example.com,true
Jane Smith,25,jane@example.com,false
```

#### JSONL Files

```python
from schema_generation import generate_schema

# Generate schema from JSONL
schema = generate_schema("data.jsonl")

# Without business type inference
schema = generate_schema("data.jsonl", use_business_types=False)

# With custom sampling
schema = generate_schema("data.jsonl", sample_rows=200)
```

**JSONL Example:**
```jsonl
{"name": "John", "age": 30, "email": "john@example.com", "tags": ["developer", "python"]}
{"name": "Jane", "age": 25, "email": "jane@example.com", "tags": ["designer"], "address": {"city": "NYC"}}
```

**Nested Objects:**
```python
# JSONL with nested objects
schema = generate_schema("nested_data.jsonl")

# Access nested properties
user_schema = schema["properties"]["user"]
address_schema = user_schema["properties"]["address"]
```

#### Parquet Files

```python
from schema_generation import generate_schema

# Generate schema from Parquet
schema = generate_schema("data.parquet")

# Without business type inference
schema = generate_schema("data.parquet", use_business_types=False)

# With custom sampling
schema = generate_schema("data.parquet", sample_rows=50)
```

**Note:** Parquet support requires `pyarrow` to be installed:
```bash
pip install pyarrow
```

#### Explicit File Type

If a file doesn't have a standard extension, you can specify the type explicitly:

```python
# File without extension
schema = generate_schema("data.txt", file_type="csv")

# File with ambiguous extension
schema = generate_schema("data.dat", file_type="jsonl")
```

### File Type Detection

You can also detect the file type without generating a schema:

```python
from schema_generation import detect_file_type

file_type = detect_file_type("data.csv")  # Returns 'csv'
file_type = detect_file_type("data.jsonl")  # Returns 'jsonl'
file_type = detect_file_type("data.parquet")  # Returns 'parquet'
```

## Supported File Types

### CSV (.csv)
- Comma-separated values
- First row treated as headers
- Always uses business type inference

### JSONL (.jsonl, .jsonlines, .ndjson)
- One JSON object per line
- Supports nested objects and arrays
- Handles arrays of objects

### Parquet (.parquet, .parq)
- Columnar storage format
- Preserves Parquet type information
- Requires `pyarrow` library

## Business Types Detected

The library can detect the following business types:

- `email` - Email addresses
- `url` - URLs (http/https)
- `phone_number` - Phone numbers
- `uuid` - UUIDs
- `ip_address` - IPv4 addresses
- `ipv6_address` - IPv6 addresses
- `mac_address` - MAC addresses
- `credit_card` - Credit card numbers
- `date` - Dates
- `datetime` - Date and time
- `timestamp` - Unix timestamps
- `currency` - Currency values ($, €, £, etc.)
- `percentage` - Percentage values
- `postal_code` - Postal/ZIP codes
- `isbn` - ISBN numbers
- `json` - JSON strings
- `array` - Comma-separated arrays
- `hex_color` - Hex color codes
- `base64` - Base64 encoded strings

## Error Handling

The function raises appropriate exceptions:

```python
from schema_generation import generate_schema

try:
    schema = generate_schema("data.csv")
except FileNotFoundError:
    print("File not found")
except ValueError as e:
    print(f"Unsupported file type: {e}")
except ImportError as e:
    print(f"Missing dependency: {e}")
```

**Common Exceptions:**

- `FileNotFoundError`: File doesn't exist
- `ValueError`: Unsupported file type or cannot determine type
- `ImportError`: Missing `pyarrow` for Parquet files
- `json.JSONDecodeError`: Invalid JSON in JSONL files

## Advanced Usage

### Working with Nested Structures (JSONL)

```python
schema = generate_schema("nested_data.jsonl")

# Access nested object properties
user_props = schema["properties"]["user"]["properties"]
print(user_props["name"]["type"])  # 'string'

# Access array item schemas
tags_items = schema["properties"]["tags"]["items"]
print(tags_items["type"])  # 'string'
```

### Custom Sampling

For large files, you can limit the number of rows sampled:

```python
# Sample only first 50 rows
schema = generate_schema("large_file.csv", sample_rows=50)
```

### Disabling Business Types

If you only need data types (not business types):

```python
# JSONL and Parquet only (CSV always uses business types)
schema = generate_schema("data.jsonl", use_business_types=False)
schema = generate_schema("data.parquet", use_business_types=False)
```

## Project Structure

```
schema/
├── src/
│   └── schema_generation/
│       ├── __init__.py
│       ├── schema_generator.py      # Unified interface
│       ├── common/
│       │   └── data_infer.py         # Type inference
│       ├── csv/
│       │   └── csv_schema_generator.py
│       ├── jsonl/
│       │   └── jsonl_schema_generator.py
│       └── parquet/
│           └── parquet_schema_generator.py
├── tests/
│   └── schema_generation/
│       ├── common/
│       ├── csv/
│       ├── jsonl/
│       └── parquet/
├── requirements.txt
└── requirements-dev.txt
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/schema_generation/csv/test_csv_schema_generator.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

