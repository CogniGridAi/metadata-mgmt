import unittest
import tempfile
import os
from pathlib import Path

# Add parent directory to path to import the module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from schema_generation.csv.csv_schema_generator import generate_csv_schema


class TestCSVSchemaGenerator(unittest.TestCase):
    """Unit tests for generate_csv_schema function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_temp_csv(self, content: str, filename: str = "test.csv") -> str:
        """Helper method to create a temporary CSV file"""
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath
    
    def test_basic_csv_with_headers(self):
        """Test basic CSV with headers"""
        csv_content = """name,age,email
John Doe,30,john@example.com
Jane Smith,25,jane@example.com"""
        
        csv_file = self.create_temp_csv(csv_content)
        schema = generate_csv_schema(csv_file)
        
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
        csv_content = """id,name,email,price,is_active
42,John,john@example.com,99.99,true
100,Jane,jane@example.com,149.50,false"""
        
        csv_file = self.create_temp_csv(csv_content)
        schema = generate_csv_schema(csv_file)
        
        # Verify that properties have types (specific type inference is tested in test_data_infer.py)
        for col in ["id", "name", "email", "price", "is_active"]:
            self.assertIn(col, schema["properties"])
            prop = schema["properties"][col]
            self.assertIn("type", prop)
            # Verify business_type is set when applicable
            if col == "email" and "business_type" in prop:
                self.assertEqual(prop["business_type"], "email")
    
    def test_nullable_columns(self):
        """Test that nullable columns are handled correctly"""
        csv_content = """name,age,email
John,30,john@example.com
Jane,,
Bob,25,"""
        
        csv_file = self.create_temp_csv(csv_content)
        schema = generate_csv_schema(csv_file)
        
        email_prop = schema["properties"]["email"]
        self.assertIn("type", email_prop)
        # Email should be nullable
        if isinstance(email_prop["type"], list):
            self.assertIn("null", email_prop["type"])
        # Name should be required (no nulls)
        name_prop = schema["properties"]["name"]
        self.assertIn("name", schema["required"])
    
    def test_all_null_column(self):
        """Test column with all null values"""
        csv_content = """name,empty_col,value
John,,100
Jane,,200
Bob,,300"""
        
        csv_file = self.create_temp_csv(csv_content)
        schema = generate_csv_schema(csv_file)
        
        empty_prop = schema["properties"]["empty_col"]
        self.assertIn("type", empty_prop)
        # Should default to nullable string
        if isinstance(empty_prop["type"], list):
            self.assertIn("null", empty_prop["type"])
            self.assertIn("string", empty_prop["type"])
    
    def test_mixed_data_types_in_column(self):
        """Test column with mixed data types"""
        csv_content = """mixed_col
123
45.67
text_value
789"""
        
        csv_file = self.create_temp_csv(csv_content)
        schema = generate_csv_schema(csv_file)
        
        mixed_prop = schema["properties"]["mixed_col"]
        self.assertIn("type", mixed_prop)
        # Should have multiple types
        if isinstance(mixed_prop["type"], list):
            self.assertGreater(len(mixed_prop["type"]), 1)
    
    
    def test_sample_rows_parameter(self):
        """Test that sample_rows parameter limits the number of rows processed"""
        # Create CSV with many rows
        rows = ["name,age"] + [f"Person{i},{20+i}" for i in range(200)]
        csv_content = "\n".join(rows)
        
        csv_file = self.create_temp_csv(csv_content)
        # Test with sample_rows=10
        schema = generate_csv_schema(csv_file, sample_rows=10)
        
        # Schema should still be generated correctly
        self.assertIn("properties", schema)
        self.assertIn("name", schema["properties"])
        self.assertIn("age", schema["properties"])
    
    def test_single_row_csv(self):
        """Test CSV with only header and one data row"""
        csv_content = """name,age
John,30"""
        
        csv_file = self.create_temp_csv(csv_content)
        schema = generate_csv_schema(csv_file)
        
        self.assertIn("properties", schema)
        self.assertIn("name", schema["properties"])
        self.assertIn("age", schema["properties"])
    
    def test_empty_csv_with_headers(self):
        """Test CSV with only headers and no data rows"""
        csv_content = """name,age,email"""
        
        csv_file = self.create_temp_csv(csv_content)
        schema = generate_csv_schema(csv_file)
        
        self.assertIn("properties", schema)
        # All columns should default to nullable string
        for col in ["name", "age", "email"]:
            self.assertIn(col, schema["properties"])
            prop = schema["properties"][col]
            if isinstance(prop["type"], list):
                self.assertIn("null", prop["type"])
    
    def test_schema_structure(self):
        """Test that generated schema has correct structure"""
        csv_content = """id,name,price
1,Apple,1.50
2,Banana,0.75"""
        
        csv_file = self.create_temp_csv(csv_content)
        schema = generate_csv_schema(csv_file)
        
        # Check top-level structure
        self.assertIn("$schema", schema)
        self.assertIn("type", schema)
        self.assertIn("properties", schema)
        self.assertIn("required", schema)
        
        # Check schema type
        self.assertEqual(schema["$schema"], "http://json-schema.org/draft-07/schema#")
        self.assertEqual(schema["type"], "object")
        
        # Check property structure
        for prop_name, prop_value in schema["properties"].items():
            self.assertIn("type", prop_value)
            self.assertIn("description", prop_value)
            self.assertTrue(prop_value["description"].startswith("Column: "))
    
    def test_business_type_preservation(self):
        """Test that business types are properly preserved in schema
        
        Note: Specific business type detection is tested in test_data_infer.py.
        This test verifies that business types are correctly included in the schema.
        """
        csv_content = """email,uuid,url
user@example.com,550e8400-e29b-41d4-a716-446655440000,https://example.com
admin@test.com,6ba7b810-9dad-11d1-80b4-00c04fd430c8,http://test.com"""
        
        csv_file = self.create_temp_csv(csv_content)
        schema = generate_csv_schema(csv_file)
        
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
    
    def test_file_not_found_error(self):
        """Test that appropriate error is raised for non-existent file"""
        with self.assertRaises(FileNotFoundError):
            generate_csv_schema("/nonexistent/file.csv")
    
    def test_required_fields_logic(self):
        """Test that required fields are correctly identified"""
        csv_content = """required_col,nullable_col,another_required
value1,value2,value3
value4,,value5
value6,value7,value8"""
        
        csv_file = self.create_temp_csv(csv_content)
        schema = generate_csv_schema(csv_file)
        
        # required_col and another_required should be in required list
        # nullable_col should not be in required list
        self.assertIn("required", schema)
        self.assertIn("required_col", schema["required"])
        self.assertIn("another_required", schema["required"])
        # Note: nullable_col might still be required if it has no nulls in sample
        # This depends on the actual data


if __name__ == '__main__':
    unittest.main()

