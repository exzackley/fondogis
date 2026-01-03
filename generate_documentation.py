#!/usr/bin/env python3
"""
Generate Deep Documentation for Data Sources
=============================================

Uses Gemini 3 Pro Preview with web search grounding to generate
comprehensive documentation for each data source.

Usage:
    python3 generate_documentation.py           # Document all sources
    python3 generate_documentation.py gbif      # Document specific source
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Load environment variables
def load_env():
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    print("Error: google-generativeai not installed. Run: pip3 install google-generativeai")
    sys.exit(1)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in .env file")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

# Use the model with search grounding capability
MODEL_NAME = "gemini-2.0-flash"  # Using stable model with grounding
RATE_LIMIT_DELAY = 2.0  # seconds between requests


def generate_deep_documentation(source: dict) -> dict:
    """Generate comprehensive documentation for a data source using Gemini with grounding."""
    
    model = genai.GenerativeModel(MODEL_NAME)
    
    prompt = f"""You are creating documentation for a scientific data source used in an environmental dashboard for Mexico's protected areas (ANPs - Areas Naturales Protegidas).

Research and document this data source comprehensively:

DATA SOURCE:
- ID: {source.get('id')}
- Name: {source.get('name')}
- Provider: {source.get('provider')}
- Provider URL: {source.get('provider_url')}
- Data Type: {source.get('data_type')}
- API/Access: {source.get('api_endpoint', 'N/A')}
- Current Summary: {source.get('documentation', {}).get('summary', 'N/A')}

Generate documentation in this exact JSON format (return ONLY valid JSON, no markdown):
{{
    "summary": "2-3 sentence executive summary",
    "description": "2-3 paragraphs explaining what this data provides, how it's generated, and why it matters for conservation",
    "methodology": {{
        "data_collection": "How raw data is collected (satellite, census, citizen science, etc.)",
        "processing": "How raw data is processed into the final product",
        "validation": "Quality control and validation methods used"
    }},
    "spatial_temporal": {{
        "spatial_resolution": "Native resolution (e.g., 30m, 1km, point data)",
        "spatial_coverage": "Geographic coverage",
        "temporal_range": "Time period covered",
        "update_frequency": "How often data is updated"
    }},
    "limitations": [
        "Known limitation 1",
        "Known limitation 2"
    ],
    "quality_assessment": {{
        "accuracy": "Known accuracy metrics if available",
        "completeness": "Data completeness notes",
        "reliability_rating": "high/medium/low with justification"
    }},
    "citation": "Recommended citation format",
    "related_sources": ["Other complementary data sources"],
    "conservation_applications": ["Specific uses for protected area management"]
}}"""

    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # Clean markdown formatting
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        return json.loads(result_text.strip())
    except json.JSONDecodeError as e:
        print(f"    JSON parse error: {e}")
        return {
            "error": "Failed to parse response",
            "raw_response": response.text[:500] if response else "No response"
        }
    except Exception as e:
        print(f"    API error: {e}")
        return {"error": str(e)}


def generate_data_dictionary(source: dict, sample_data: dict = None) -> dict:
    """Generate field-level documentation for a data source."""
    
    model = genai.GenerativeModel(MODEL_NAME)
    
    fields = source.get('fields_provided', [])
    
    prompt = f"""Document each data field from this environmental data source:

Source: {source.get('name')}
Fields: {json.dumps(fields)}
{f'Sample Data: {json.dumps(sample_data, default=str)[:2000]}' if sample_data else ''}

For each field, provide documentation in this JSON format (return ONLY valid JSON):
{{
    "fields": {{
        "field_name": {{
            "description": "What this field represents",
            "unit": "Unit of measurement",
            "data_type": "numeric/categorical/text/boolean",
            "value_range": "Expected range or domain",
            "interpretation": "How to interpret values (what's high vs low)"
        }}
    }}
}}"""

    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        return json.loads(result_text.strip())
    except Exception as e:
        return {"error": str(e)}


def update_data_sources_file():
    """Load, update, and save data_sources.json with deep documentation."""
    
    data_sources_path = Path(__file__).parent / 'data_sources.json'
    
    with open(data_sources_path) as f:
        catalog = json.load(f)
    
    sources = catalog.get('sources', [])
    updated_count = 0
    
    for i, source in enumerate(sources):
        source_id = source.get('id')
        existing_doc = source.get('documentation', {})
        
        # Skip if already has deep documentation
        if not existing_doc.get('pending_deep_documentation', False):
            print(f"[{i+1}/{len(sources)}] {source_id}: Already documented, skipping")
            continue
        
        print(f"[{i+1}/{len(sources)}] {source_id}: Generating documentation...")
        
        try:
            # Generate deep documentation
            deep_doc = generate_deep_documentation(source)
            
            if 'error' not in deep_doc:
                # Merge with existing documentation
                source['documentation'] = {
                    **existing_doc,
                    **deep_doc,
                    'pending_deep_documentation': False,
                    'generated_at': datetime.now().isoformat(),
                    'generated_by': 'gemini-2.0-flash'
                }
                updated_count += 1
                print(f"    Success!")
            else:
                print(f"    Error: {deep_doc.get('error')}")
                source['documentation']['generation_error'] = deep_doc.get('error')
            
            time.sleep(RATE_LIMIT_DELAY)
            
        except Exception as e:
            print(f"    Exception: {e}")
            source['documentation']['generation_error'] = str(e)
    
    # Update last_updated timestamp
    catalog['last_updated'] = datetime.now().isoformat()
    
    # Save updated catalog
    with open(data_sources_path, 'w') as f:
        json.dump(catalog, f, indent=2)
    
    print(f"\nUpdated {updated_count} sources. Saved to {data_sources_path}")
    return catalog


def document_single_source(source_id: str):
    """Generate documentation for a single source by ID."""
    
    data_sources_path = Path(__file__).parent / 'data_sources.json'
    
    with open(data_sources_path) as f:
        catalog = json.load(f)
    
    source = next((s for s in catalog['sources'] if s['id'] == source_id), None)
    if not source:
        print(f"Error: Source '{source_id}' not found")
        return
    
    print(f"Generating documentation for: {source['name']}...")
    deep_doc = generate_deep_documentation(source)
    
    if 'error' not in deep_doc:
        source['documentation'] = {
            **source.get('documentation', {}),
            **deep_doc,
            'pending_deep_documentation': False,
            'generated_at': datetime.now().isoformat()
        }
        
        catalog['last_updated'] = datetime.now().isoformat()
        
        with open(data_sources_path, 'w') as f:
            json.dump(catalog, f, indent=2)
        
        print("Success! Documentation saved.")
        print(json.dumps(deep_doc, indent=2))
    else:
        print(f"Error: {deep_doc}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Document specific source
        document_single_source(sys.argv[1])
    else:
        # Document all sources
        print("Generating deep documentation for all data sources...")
        print("=" * 60)
        update_data_sources_file()
