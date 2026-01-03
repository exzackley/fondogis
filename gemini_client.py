#!/usr/bin/env python3
"""
Gemini API Client for Documentation Generation
===============================================

Uses Google's Gemini 3 Pro Preview model to generate rich documentation
for data sources, data dictionaries, and analysis summaries.

Requires: GEMINI_API_KEY in .env file
"""

import json
import os
import time
from pathlib import Path

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    print("Warning: google-generativeai not installed. Run: pip install google-generativeai")

# Load environment variables
def load_env():
    """Load environment variables from .env file."""
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

# Configuration
GEMINI_MODEL = "gemini-3-pro-preview"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Rate limiting
GEMINI_DELAY = 1.0  # seconds between requests


def init_gemini():
    """Initialize Gemini client."""
    if not HAS_GENAI:
        raise RuntimeError("google-generativeai package not installed")
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not found in environment")
    
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel(GEMINI_MODEL)


def generate_source_documentation(source_info: dict, web_context: str = None) -> dict:
    """
    Generate comprehensive documentation for a data source.
    
    Args:
        source_info: Basic info about the source (name, url, data_type)
        web_context: Optional web search results to include as context
    
    Returns:
        dict with summary, full_description, methodology, limitations, citation
    """
    model = init_gemini()
    
    prompt = f"""You are documenting a data source for an environmental data dashboard tracking Mexico's protected areas (ANPs).

DATA SOURCE INFO:
- Name: {source_info.get('name')}
- Provider: {source_info.get('provider')}
- URL: {source_info.get('provider_url')}
- Data Type: {source_info.get('data_type')}
- API/Access: {source_info.get('api_endpoint', 'N/A')}

{f'ADDITIONAL CONTEXT FROM WEB SEARCH:{chr(10)}{web_context}' if web_context else ''}

Generate comprehensive documentation in JSON format with these fields:
{{
    "summary": "2-3 sentence concise summary for quick reference",
    "full_description": "Detailed 2-3 paragraph description of what this data source provides, how it's collected, and its significance for conservation",
    "methodology": "How the data is collected/generated (remote sensing, citizen science, census, etc.)",
    "spatial_coverage": "Global, Mexico-specific, or regional coverage details",
    "temporal_coverage": "Time range of data, update frequency",
    "known_limitations": ["List of known limitations or caveats"],
    "data_quality_notes": "Notes on reliability, accuracy, completeness",
    "recommended_citation": "Proper citation format if available",
    "related_sources": ["Other data sources that complement this one"],
    "use_cases": ["Specific use cases for ANP analysis"]
}}

Return ONLY valid JSON, no markdown formatting."""

    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # Clean up any markdown code blocks
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        
        return json.loads(result_text)
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse Gemini response: {e}", "raw": response.text}
    except Exception as e:
        return {"error": str(e)}


def generate_field_documentation(field_name: str, sample_values: list, context: str = None) -> dict:
    """
    Generate documentation for a data field.
    
    Args:
        field_name: Name of the field
        sample_values: Sample values from the field
        context: Additional context about the field's source
    
    Returns:
        dict with description, unit, range, interpretation
    """
    model = init_gemini()
    
    prompt = f"""Document this data field from an environmental dataset for Mexico's protected areas:

Field Name: {field_name}
Sample Values: {sample_values[:10]}
{f'Context: {context}' if context else ''}

Generate documentation in JSON format:
{{
    "description": "Clear explanation of what this field represents",
    "unit": "Unit of measurement (if applicable)",
    "value_range": "Expected range or domain of values",
    "interpretation": "How to interpret high/low values",
    "data_type": "numeric, categorical, text, etc.",
    "source_dataset": "Original dataset this comes from (if identifiable)"
}}

Return ONLY valid JSON."""

    try:
        time.sleep(GEMINI_DELAY)
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        
        return json.loads(result_text)
    except Exception as e:
        return {"error": str(e)}


def generate_anp_summary(anp_data: dict) -> str:
    """
    Generate a natural language summary of an ANP's data.
    
    Args:
        anp_data: Full ANP data dict
    
    Returns:
        Human-readable summary paragraph
    """
    model = init_gemini()
    
    prompt = f"""Write a concise 3-4 sentence summary of this Mexican protected area based on its data:

{json.dumps(anp_data, indent=2, default=str)[:8000]}

Focus on: location, size, key environmental features, biodiversity highlights, and any notable concerns (deforestation, population pressure, etc.).

Write in a factual, scientific tone suitable for a conservation report."""

    try:
        time.sleep(GEMINI_DELAY)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating summary: {e}"


def batch_document_sources(sources: list) -> list:
    """
    Document multiple data sources with rate limiting.
    
    Args:
        sources: List of source info dicts
    
    Returns:
        List of documented sources
    """
    documented = []
    for i, source in enumerate(sources):
        print(f"  Documenting [{i+1}/{len(sources)}]: {source.get('name')}...")
        try:
            doc = generate_source_documentation(source)
            source['documentation'] = doc
            documented.append(source)
        except Exception as e:
            print(f"    Error: {e}")
            source['documentation'] = {"error": str(e)}
            documented.append(source)
        
        time.sleep(GEMINI_DELAY)
    
    return documented


# CLI interface
if __name__ == "__main__":
    import sys
    
    if not HAS_GENAI:
        print("Install google-generativeai: pip install google-generativeai")
        sys.exit(1)
    
    if not GEMINI_API_KEY:
        print("Set GEMINI_API_KEY in .env file")
        sys.exit(1)
    
    # Test the client
    print("Testing Gemini client...")
    test_source = {
        "name": "GBIF Species Occurrences",
        "provider": "Global Biodiversity Information Facility",
        "provider_url": "https://gbif.org",
        "data_type": "biodiversity"
    }
    
    result = generate_source_documentation(test_source)
    print(json.dumps(result, indent=2))
