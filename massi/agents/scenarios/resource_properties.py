from jsonschema.validators import Draft202012Validator


class Defaults:

    # Adapted from MIAGIS JSON Schema
    # @see: https://moseleybioinformaticslab.github.io/miagis/jsonschema.html
    resource_properties_metadata_json_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "location": {"type": "string", "minLength": 1},
            "alternate_locations": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "minItems": 1,
            },
            "type": {"type": "string", "minLength": 1},
            "fairness": {"type": "string", "pattern": "(?i)^f?a?i?r?$"},
            "format": {"type": "string", "minLength": 1},
            "schema": {"type": ["string", "object"], "minLength": 1},
            "sources": {"type": "array", "items": {"type": "string", "minLength": 1}},
            "description": {"type": "string", "minLength": 1},
            "creator": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "type": {
                            "type": "string",
                            "minLength": 1,
                            "enum": ["URL", "organization", "author", "DOI"],
                        },
                    },
                    "required": ["name", "type"],
                },
            },
            "spatial_metadata": {  # Addition inspired on ISO-19115
                "type": "object",
                "properties": {
                    "geography_name": {"type": "string"},
                    "bbox": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4,
                        "description": "[min_lon, min_lat, max_lon, max_lat]",
                    },
                    "crs": {"type": "string"},
                    "update_frequency": {
                        "type": "string",
                        "enum": ["daily", "monthly", "annually", "as_needed", "static"],
                    },
                },
            },
        },
        "required": ["location", "type", "fairness", "format", "description"],
    }
    resource_properties_metadata_json_schema_validator = Draft202012Validator(
        resource_properties_metadata_json_schema
    )
