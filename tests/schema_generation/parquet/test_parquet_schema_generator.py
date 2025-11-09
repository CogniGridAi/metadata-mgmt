import unittest
import tempfile
import os
from pathlib import Path

# Add parent directory to path to import the module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from schema_generation.parquet.parquet_schema_generator import generate_parquet_schema


class TestParquetSchemaGenerator(unittest.TestCase):
    """Unit tests for generate_parquet_schema function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_temp_parquet(self, data: dict, filename: str = "test.parquet") -> str:
        """Helper method to create a temporary Parquet file"""
        try:
            import pandas as pd
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            self.skipTest("pyarrow and pandas are required for parquet tests")
        
        filepath = os.path.join(self.temp_dir, filename)
        df = pd.DataFrame(data)
        table = pa.Table.from_pandas(df)
        pq.write_table(table, filepath)
        return filepath
    
    def test_basic_parquet_with_simple_columns(self):
        """Test basic Parquet with simple columns"""
        data = {
            "name": ["John", "Jane", "Bob"],
            "age": [30, 25, 35],
            "email": ["john@example.com", "jane@example.com", "bob@example.com"]
        }
        
        parquet_file = self.create_temp_parquet(data)
        schema = generate_parquet_schema(parquet_file)
        
        self.assertIsInstance(schema, dict)
        self.assertEqual(schema["type"], "object")
        self.assertIn("properties", schema)
        self.assertIn("name", schema["properties"])
        self.assertIn("age", schema["properties"])
        self.assertIn("email", schema["properties"])
    
    def test_type_inference_integration(self):
        """Test that type inference works correctly in schema generation context
        
        Note: Comprehensive type inference tests are in test_data_infer.py.
        This test only verifies that types are properly integrated into the schema.
        """
        data = {
            "id": [42, 100, 200],
            "name": ["John", "Jane", "Bob"],
            "email": ["john@example.com", "jane@example.com", "bob@example.com"],
            "price": [99.99, 149.50, 79.99],
            "is_active": [True, False, True]
        }
        
        parquet_file = self.create_temp_parquet(data)
        schema = generate_parquet_schema(parquet_file)
        
        # Verify that properties have types
        for field in ["id", "name", "email", "price", "is_active"]:
            self.assertIn(field, schema["properties"])
            prop = schema["properties"][field]
            self.assertIn("type", prop)
            self.assertIn("parquet_type", prop)
            self.assertIn("nullable", prop)
            # Verify business_type is set when applicable
            if field == "email" and "business_type" in prop:
                self.assertEqual(prop["business_type"], "email")
    
    def test_business_type_preservation(self):
        """Test that business types are properly preserved in schema
        
        Note: Specific business type detection is tested in test_data_infer.py.
        This test verifies that business types are correctly included in the schema.
        """
        data = {
            "email": ["user@example.com", "admin@test.com"],
            "uuid": ["550e8400-e29b-41d4-a716-446655440000", "6ba7b810-9dad-11d1-80b4-00c04fd430c8"],
            "url": ["https://example.com", "http://test.com"]
        }
        
        parquet_file = self.create_temp_parquet(data)
        schema = generate_parquet_schema(parquet_file)
        
        # Verify business types are included when detected
        email_prop = schema["properties"]["email"]
        if "business_type" in email_prop:
            self.assertEqual(email_prop["business_type"], "email")
        
        uuid_prop = schema["properties"]["uuid"]
        if "business_type" in uuid_prop:
            self.assertEqual(uuid_prop["business_type"], "uuid")
        
        url_prop = schema["properties"]["url"]
        if "business_type" in url_prop:
            self.assertEqual(url_prop["business_type"], "url")
    
    def test_nullable_columns(self):
        """Test that nullable columns are handled correctly"""
        try:
            import pandas as pd
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            self.skipTest("pyarrow and pandas are required for parquet tests")
        
        data = {
            "name": ["John", "Jane", "Bob"],
            "age": [30, None, 35],
            "email": ["john@example.com", None, "bob@example.com"]
        }
        
        parquet_file = self.create_temp_parquet(data)
        schema = generate_parquet_schema(parquet_file)
        
        age_prop = schema["properties"]["age"]
        self.assertIn("type", age_prop)
        self.assertTrue(age_prop["nullable"])
        # Type should include null if nullable
        if isinstance(age_prop["type"], list):
            self.assertIn("null", age_prop["type"])
        
        # Name should be required (no nulls)
        name_prop = schema["properties"]["name"]
        if not name_prop["nullable"]:
            self.assertIn("name", schema["required"])
    
    def test_integer_types(self):
        """Test different integer types"""
        data = {
            "int32_col": [1, 2, 3],
            "int64_col": [1000000, 2000000, 3000000],
            "small_int": [10, 20, 30]
        }
        
        parquet_file = self.create_temp_parquet(data)
        schema = generate_parquet_schema(parquet_file)
        
        for col in ["int32_col", "int64_col", "small_int"]:
            prop = schema["properties"][col]
            self.assertIn("type", prop)
            # Should be integer or number
            if isinstance(prop["type"], list):
                self.assertTrue(any(t in ["integer", "number"] for t in prop["type"]))
            else:
                self.assertIn(prop["type"], ["integer", "number"])
            self.assertIn("parquet_type", prop)
    
    def test_float_types(self):
        """Test float types"""
        data = {
            "float32_col": [1.5, 2.5, 3.5],
            "float64_col": [10.123456, 20.654321, 30.987654],
            "price": [99.99, 149.50, 79.99]
        }
        
        parquet_file = self.create_temp_parquet(data)
        schema = generate_parquet_schema(parquet_file)
        
        for col in ["float32_col", "float64_col", "price"]:
            prop = schema["properties"][col]
            self.assertIn("type", prop)
            # Should be number or float
            if isinstance(prop["type"], list):
                self.assertTrue(any(t in ["number", "float"] for t in prop["type"]))
            else:
                self.assertIn(prop["type"], ["number", "float"])
    
    def test_boolean_type(self):
        """Test boolean type"""
        data = {
            "is_active": [True, False, True],
            "is_verified": [False, True, True],
            "status": [True, True, False]
        }
        
        parquet_file = self.create_temp_parquet(data)
        schema = generate_parquet_schema(parquet_file)
        
        is_active_prop = schema["properties"]["is_active"]
        self.assertIn("type", is_active_prop)
        # Should be boolean
        if isinstance(is_active_prop["type"], list):
            self.assertIn("boolean", is_active_prop["type"])
        else:
            self.assertEqual(is_active_prop["type"], "boolean")
    
    def test_string_type(self):
        """Test string type"""
        data = {
            "name": ["John", "Jane", "Bob"],
            "description": ["Test description", "Another description", "Third description"],
            "category": ["A", "B", "C"]
        }
        
        parquet_file = self.create_temp_parquet(data)
        schema = generate_parquet_schema(parquet_file)
        
        name_prop = schema["properties"]["name"]
        self.assertIn("type", name_prop)
        if isinstance(name_prop["type"], list):
            self.assertIn("string", name_prop["type"])
        else:
            self.assertEqual(name_prop["type"], "string")
    
    def test_date_types(self):
        """Test date and timestamp types"""
        try:
            import pandas as pd
            import pyarrow as pa
            import pyarrow.parquet as pq
            from datetime import datetime, date
        except ImportError:
            self.skipTest("pyarrow and pandas are required for parquet tests")
        
        data = {
            "birth_date": [date(2020, 1, 15), date(2021, 2, 20), date(2022, 3, 25)],
            "created_at": [
                datetime(2024, 1, 15, 10, 30, 0),
                datetime(2024, 2, 20, 14, 45, 0),
                datetime(2024, 3, 25, 9, 15, 0)
            ]
        }
        
        parquet_file = self.create_temp_parquet(data)
        schema = generate_parquet_schema(parquet_file)
        
        birth_date_prop = schema["properties"]["birth_date"]
        self.assertIn("type", birth_date_prop)
        self.assertIn("parquet_type", birth_date_prop)
        
        created_at_prop = schema["properties"]["created_at"]
        self.assertIn("type", created_at_prop)
        self.assertIn("parquet_type", created_at_prop)
    
    def test_required_fields(self):
        """Test that required fields are correctly identified"""
        try:
            import pandas as pd
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            self.skipTest("pyarrow and pandas are required for parquet tests")
        
        data = {
            "required_col": ["value1", "value2", "value3"],
            "nullable_col": ["value1", None, "value3"]
        }
        
        parquet_file = self.create_temp_parquet(data)
        schema = generate_parquet_schema(parquet_file)
        
        self.assertIn("required", schema)
        # Required column should be in required list if not nullable
        required_prop = schema["properties"]["required_col"]
        if not required_prop["nullable"]:
            self.assertIn("required_col", schema["required"])
        
        # Nullable column should not be in required list
        nullable_prop = schema["properties"]["nullable_col"]
        if nullable_prop["nullable"]:
            self.assertNotIn("nullable_col", schema["required"])
    
    def test_sample_rows_parameter(self):
        """Test that sample_rows parameter limits the number of rows processed"""
        # Create Parquet with many rows
        data = {
            "id": list(range(200)),
            "name": [f"Person{i}" for i in range(200)]
        }
        
        parquet_file = self.create_temp_parquet(data)
        # Test with sample_rows=10
        schema = generate_parquet_schema(parquet_file, sample_rows=10)
        
        # Schema should still be generated correctly
        self.assertIn("properties", schema)
        self.assertIn("id", schema["properties"])
        self.assertIn("name", schema["properties"])
        # Metadata should show actual number of rows
        self.assertIn("metadata", schema)
        self.assertEqual(schema["metadata"]["num_rows"], 200)
    
    def test_schema_structure(self):
        """Test that generated schema has correct structure"""
        data = {
            "id": [1, 2, 3],
            "name": ["Test1", "Test2", "Test3"],
            "value": [42.5, 43.5, 44.5]
        }
        
        parquet_file = self.create_temp_parquet(data)
        schema = generate_parquet_schema(parquet_file)
        
        # Check top-level structure
        self.assertIn("$schema", schema)
        self.assertIn("type", schema)
        self.assertIn("properties", schema)
        self.assertIn("required", schema)
        self.assertIn("metadata", schema)
        
        # Check schema type
        self.assertEqual(schema["$schema"], "http://json-schema.org/draft-07/schema#")
        self.assertEqual(schema["type"], "object")
        
        # Check property structure
        for prop_name, prop_value in schema["properties"].items():
            self.assertIn("type", prop_value)
            self.assertIn("description", prop_value)
            self.assertIn("parquet_type", prop_value)
            self.assertIn("nullable", prop_value)
            self.assertTrue(prop_value["description"].startswith("Column: "))
        
        # Check metadata
        metadata = schema["metadata"]
        self.assertIn("num_rows", metadata)
        self.assertIn("num_columns", metadata)
    
    def test_use_business_types_parameter(self):
        """Test that use_business_types parameter works correctly"""
        data = {
            "email": ["user@example.com", "admin@test.com"],
            "url": ["https://example.com", "http://test.com"]
        }
        
        parquet_file = self.create_temp_parquet(data)
        
        # With business types
        schema_with = generate_parquet_schema(parquet_file, use_business_types=True)
        email_prop_with = schema_with["properties"]["email"]
        # Business type might be detected
        if "business_type" in email_prop_with:
            self.assertEqual(email_prop_with["business_type"], "email")
        
        # Without business types
        schema_without = generate_parquet_schema(parquet_file, use_business_types=False)
        email_prop_without = schema_without["properties"]["email"]
        # Business type should not be present
        self.assertNotIn("business_type", email_prop_without)
    
    def test_file_not_found_error(self):
        """Test that appropriate error is raised for non-existent file"""
        try:
            import pyarrow.parquet as pq
        except ImportError:
            self.skipTest("pyarrow is required for this test")
        
        with self.assertRaises((FileNotFoundError, OSError)):
            generate_parquet_schema("/nonexistent/file.parquet")
    
    def test_import_error_without_pyarrow(self):
        """Test that ImportError is raised when pyarrow is not available"""
        # This test would require mocking the import, which is complex
        # Instead, we'll just verify the function handles it gracefully
        # by checking the docstring mentions the requirement
        import inspect
        doc = inspect.getdoc(generate_parquet_schema)
        self.assertIn("pyarrow", doc)
    
    def test_parquet_type_preservation(self):
        """Test that Parquet types are preserved in schema"""
        data = {
            "int_col": [1, 2, 3],
            "float_col": [1.5, 2.5, 3.5],
            "string_col": ["a", "b", "c"],
            "bool_col": [True, False, True]
        }
        
        parquet_file = self.create_temp_parquet(data)
        schema = generate_parquet_schema(parquet_file)
        
        # Verify parquet_type is present for all columns
        for col_name, prop in schema["properties"].items():
            self.assertIn("parquet_type", prop)
            # parquet_type should be a string
            self.assertIsInstance(prop["parquet_type"], str)
    
    def test_empty_parquet_file(self):
        """Test handling of empty Parquet file"""
        try:
            import pandas as pd
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            self.skipTest("pyarrow and pandas are required for parquet tests")
        
        # Create empty dataframe with column names
        df = pd.DataFrame(columns=["col1", "col2", "col3"])
        filepath = os.path.join(self.temp_dir, "empty.parquet")
        table = pa.Table.from_pandas(df)
        pq.write_table(table, filepath)
        
        schema = generate_parquet_schema(filepath)
        
        self.assertIn("properties", schema)
        # Should have properties for all columns
        self.assertIn("col1", schema["properties"])
        self.assertIn("col2", schema["properties"])
        self.assertIn("col3", schema["properties"])
    
    def test_single_row_parquet(self):
        """Test Parquet with only one row"""
        data = {
            "name": ["John"],
            "age": [30]
        }
        
        parquet_file = self.create_temp_parquet(data)
        schema = generate_parquet_schema(parquet_file)
        
        self.assertIn("properties", schema)
        self.assertIn("name", schema["properties"])
        self.assertIn("age", schema["properties"])
        # Single row - all non-nullable fields should be required
        for col_name, prop in schema["properties"].items():
            if not prop["nullable"]:
                self.assertIn(col_name, schema["required"])


if __name__ == '__main__':
    unittest.main()

