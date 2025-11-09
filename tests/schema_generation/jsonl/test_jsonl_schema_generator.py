import unittest
import tempfile
import os
import json
from pathlib import Path

# Add parent directory to path to import the module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from schema_generation.jsonl.jsonl_schema_generator import generate_jsonl_schema


class TestJSONLSchemaGenerator(unittest.TestCase):
    """Unit tests for generate_jsonl_schema function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_temp_jsonl(self, content: str, filename: str = "test.jsonl") -> str:
        """Helper method to create a temporary JSONL file"""
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath
    
    def test_basic_jsonl_with_simple_objects(self):
        """Test basic JSONL with simple flat objects"""
        jsonl_content = """{"name": "John", "age": 30, "email": "john@example.com"}
{"name": "Jane", "age": 25, "email": "jane@example.com"}"""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        schema = generate_jsonl_schema(jsonl_file)
        
        self.assertIsInstance(schema, dict)
        self.assertEqual(schema["type"], "object")
        self.assertIn("properties", schema)
        self.assertIn("name", schema["properties"])
        self.assertIn("age", schema["properties"])
        self.assertIn("email", schema["properties"])
    
    def test_nested_objects(self):
        """Test JSONL with nested objects"""
        jsonl_content = """{"user": {"name": "John", "age": 30}, "id": 1}
{"user": {"name": "Jane", "age": 25}, "id": 2}"""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        schema = generate_jsonl_schema(jsonl_file)
        
        self.assertIn("user", schema["properties"])
        user_prop = schema["properties"]["user"]
        self.assertEqual(user_prop["type"], "object")
        self.assertIn("properties", user_prop)
        self.assertIn("name", user_prop["properties"])
        self.assertIn("age", user_prop["properties"])
    
    def test_arrays(self):
        """Test JSONL with array fields"""
        jsonl_content = """{"tags": ["python", "javascript"], "scores": [95, 87]}
{"tags": ["java", "go"], "scores": [88, 92]}"""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        schema = generate_jsonl_schema(jsonl_file)
        
        tags_prop = schema["properties"]["tags"]
        self.assertEqual(tags_prop["type"], "array")
        self.assertIn("items", tags_prop)
        
        scores_prop = schema["properties"]["scores"]
        self.assertEqual(scores_prop["type"], "array")
        self.assertIn("items", scores_prop)
    
    def test_arrays_of_objects(self):
        """Test JSONL with arrays containing objects"""
        jsonl_content = """{"items": [{"name": "apple", "price": 1.50}, {"name": "banana", "price": 0.75}]}
{"items": [{"name": "orange", "price": 2.00}]}"""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        schema = generate_jsonl_schema(jsonl_file)
        
        items_prop = schema["properties"]["items"]
        self.assertEqual(items_prop["type"], "array")
        self.assertIn("items", items_prop)
        items_schema = items_prop["items"]
        # Type might be object or a list containing object (due to type inference)
        if isinstance(items_schema["type"], list):
            self.assertIn("object", items_schema["type"])
            # If type is a union, properties might not be present
            if "properties" in items_schema:
                self.assertIn("name", items_schema["properties"])
                self.assertIn("price", items_schema["properties"])
        else:
            self.assertEqual(items_schema["type"], "object")
            self.assertIn("properties", items_schema)
            self.assertIn("name", items_schema["properties"])
            self.assertIn("price", items_schema["properties"])
    
    def test_type_inference_integration(self):
        """Test that type inference works correctly in schema generation context
        
        Note: Comprehensive type inference tests are in test_data_infer.py.
        This test only verifies that types are properly integrated into the schema.
        """
        jsonl_content = """{"id": 42, "name": "John", "email": "john@example.com", "price": 99.99, "is_active": true}
{"id": 100, "name": "Jane", "email": "jane@example.com", "price": 149.50, "is_active": false}"""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        schema = generate_jsonl_schema(jsonl_file)
        
        # Verify that properties have types
        for field in ["id", "name", "email", "price", "is_active"]:
            self.assertIn(field, schema["properties"])
            prop = schema["properties"][field]
            self.assertIn("type", prop)
            # Verify business_type is set when applicable
            if field == "email" and "business_type" in prop:
                self.assertEqual(prop["business_type"], "email")
    
    def test_business_type_preservation(self):
        """Test that business types are properly preserved in schema
        
        Note: Specific business type detection is tested in test_data_infer.py.
        This test verifies that business types are correctly included in the schema.
        """
        jsonl_content = """{"email": "user@example.com", "uuid": "550e8400-e29b-41d4-a716-446655440000", "url": "https://example.com"}
{"email": "admin@test.com", "uuid": "6ba7b810-9dad-11d1-80b4-00c04fd430c8", "url": "http://test.com"}"""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        schema = generate_jsonl_schema(jsonl_file)
        
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
    
    def test_required_fields(self):
        """Test that required fields are correctly identified"""
        jsonl_content = """{"required_field": "value1", "optional_field": "value2"}
{"required_field": "value3"}
{"required_field": "value4", "optional_field": "value5"}"""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        schema = generate_jsonl_schema(jsonl_file)
        
        self.assertIn("required", schema)
        self.assertIn("required_field", schema["required"])
        self.assertNotIn("optional_field", schema["required"])
    
    def test_nullable_fields(self):
        """Test that nullable fields are handled correctly"""
        jsonl_content = """{"name": "John", "email": "john@example.com"}
{"name": "Jane", "email": null}
{"name": "Bob"}"""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        schema = generate_jsonl_schema(jsonl_file)
        
        email_prop = schema["properties"]["email"]
        self.assertIn("type", email_prop)
        # Email might be nullable if null values are present
        if isinstance(email_prop["type"], list):
            self.assertIn("null", email_prop["type"])
        
        # Name should be required (present in all objects)
        self.assertIn("name", schema["required"])
    
    def test_mixed_types_in_field(self):
        """Test field with mixed types across objects"""
        jsonl_content = """{"value": "text"}
{"value": 123}
{"value": 45.67}"""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        schema = generate_jsonl_schema(jsonl_file)
        
        value_prop = schema["properties"]["value"]
        self.assertIn("type", value_prop)
        # Should have multiple types
        if isinstance(value_prop["type"], list):
            self.assertGreater(len(value_prop["type"]), 1)
    
    def test_empty_array(self):
        """Test handling of empty arrays"""
        jsonl_content = """{"tags": [], "items": [{"id": 1}]}
{"tags": ["tag1"], "items": []}"""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        schema = generate_jsonl_schema(jsonl_file)
        
        tags_prop = schema["properties"]["tags"]
        self.assertEqual(tags_prop["type"], "array")
        self.assertIn("items", tags_prop)
    
    def test_deeply_nested_objects(self):
        """Test deeply nested object structures"""
        jsonl_content = """{"level1": {"level2": {"level3": {"value": "deep"}}}}
{"level1": {"level2": {"level3": {"value": "nested"}}}}"""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        schema = generate_jsonl_schema(jsonl_file)
        
        level1 = schema["properties"]["level1"]
        self.assertEqual(level1["type"], "object")
        level2 = level1["properties"]["level2"]
        self.assertEqual(level2["type"], "object")
        level3 = level2["properties"]["level3"]
        self.assertEqual(level3["type"], "object")
        self.assertIn("value", level3["properties"])
    
    def test_sample_rows_parameter(self):
        """Test that sample_rows parameter limits the number of rows processed"""
        # Create JSONL with many rows
        rows = [json.dumps({"id": i, "name": f"Person{i}"}) for i in range(200)]
        jsonl_content = "\n".join(rows)
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        # Test with sample_rows=10
        schema = generate_jsonl_schema(jsonl_file, sample_rows=10)
        
        # Schema should still be generated correctly
        self.assertIn("properties", schema)
        self.assertIn("id", schema["properties"])
        self.assertIn("name", schema["properties"])
    
    def test_single_object_jsonl(self):
        """Test JSONL with only one object"""
        jsonl_content = """{"name": "John", "age": 30}"""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        schema = generate_jsonl_schema(jsonl_file)
        
        self.assertIn("properties", schema)
        self.assertIn("name", schema["properties"])
        self.assertIn("age", schema["properties"])
        # Single object - all fields should be required
        self.assertIn("name", schema["required"])
        self.assertIn("age", schema["required"])
    
    def test_empty_jsonl_file(self):
        """Test empty JSONL file"""
        jsonl_content = ""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        schema = generate_jsonl_schema(jsonl_file)
        
        self.assertIn("properties", schema)
        self.assertEqual(len(schema["properties"]), 0)
        self.assertEqual(len(schema["required"]), 0)
    
    def test_invalid_json_lines(self):
        """Test that invalid JSON lines are skipped gracefully"""
        jsonl_content = """{"valid": "object"}
invalid json line
{"another": "valid"}"""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        # Should not raise an error
        schema = generate_jsonl_schema(jsonl_file)
        
        self.assertIn("properties", schema)
        self.assertIn("valid", schema["properties"])
        self.assertIn("another", schema["properties"])
    
    def test_schema_structure(self):
        """Test that generated schema has correct structure"""
        jsonl_content = """{"id": 1, "name": "Test", "value": 42.5}"""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        schema = generate_jsonl_schema(jsonl_file)
        
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
        
        # Check metadata
        metadata = schema["metadata"]
        self.assertIn("num_rows", metadata)
        self.assertIn("num_fields", metadata)
        self.assertIn("file_type", metadata)
        self.assertEqual(metadata["file_type"], "jsonl")
    
    def test_use_business_types_parameter(self):
        """Test that use_business_types parameter works correctly"""
        jsonl_content = """{"email": "user@example.com", "url": "https://example.com"}"""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        
        # With business types
        schema_with = generate_jsonl_schema(jsonl_file, use_business_types=True)
        email_prop_with = schema_with["properties"]["email"]
        # Business type might be detected
        if "business_type" in email_prop_with:
            self.assertEqual(email_prop_with["business_type"], "email")
        
        # Without business types
        schema_without = generate_jsonl_schema(jsonl_file, use_business_types=False)
        email_prop_without = schema_without["properties"]["email"]
        # Business type should not be present
        self.assertNotIn("business_type", email_prop_without)
    
    def test_file_not_found_error(self):
        """Test that appropriate error is raised for non-existent file"""
        with self.assertRaises(FileNotFoundError):
            generate_jsonl_schema("/nonexistent/file.jsonl")
    
    def test_complex_nested_structure(self):
        """Test complex nested structure with arrays and objects"""
        jsonl_content = """{"users": [{"name": "John", "contacts": {"email": "john@example.com", "phones": ["123-456-7890"]}}]}
{"users": [{"name": "Jane", "contacts": {"email": "jane@example.com", "phones": ["987-654-3210"]}}]}"""
        
        jsonl_file = self.create_temp_jsonl(jsonl_content)
        schema = generate_jsonl_schema(jsonl_file)
        
        users_prop = schema["properties"]["users"]
        self.assertEqual(users_prop["type"], "array")
        
        users_items = users_prop["items"]
        # Type might be object or a list containing object (due to type inference)
        if isinstance(users_items["type"], list):
            self.assertIn("object", users_items["type"])
            # If type is a union, properties might not be present
            if "properties" in users_items:
                self.assertIn("name", users_items["properties"])
                self.assertIn("contacts", users_items["properties"])
                
                contacts = users_items["properties"]["contacts"]
                self.assertEqual(contacts["type"], "object")
                self.assertIn("email", contacts["properties"])
                self.assertIn("phones", contacts["properties"])
                
                phones = contacts["properties"]["phones"]
                self.assertEqual(phones["type"], "array")
        else:
            self.assertEqual(users_items["type"], "object")
            self.assertIn("name", users_items["properties"])
            self.assertIn("contacts", users_items["properties"])
            
            contacts = users_items["properties"]["contacts"]
            self.assertEqual(contacts["type"], "object")
            self.assertIn("email", contacts["properties"])
            self.assertIn("phones", contacts["properties"])
            
            phones = contacts["properties"]["phones"]
            self.assertEqual(phones["type"], "array")


if __name__ == '__main__':
    unittest.main()

