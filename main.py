#!/usr/bin/env python3
"""
Medical Diagnosis Coder - Local Orchestrator
Runs the 3-step pipeline locally without external frameworks.
"""

import os
import json
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    # Example input - replace with your actual doctor notes
    raw_note = input("Enter doctor note: ").strip()
    if not raw_note:
        raw_note = "Pt has SOB and sharp chest pain upper, plus hx of DM2."

    print(f"Processing: {raw_note}")
    print("=" * 50)

    # Step 1: Clean the input
    print("Step 1: Cleaning input...")
    diagnosis_list = clean_medical_note(raw_note)
    print(f"Cleaned diagnoses: {diagnosis_list}")
    print()

    # Step 2: Search ICD-11 for each diagnosis
    print("Step 2: Searching ICD-11 database...")
    search_artifacts = []
    for diagnosis in diagnosis_list:
        print(f"  Searching for: {diagnosis}")
        results = search_icd11(diagnosis)
        search_artifacts.append({
            "diagnosis": diagnosis,
            "results": results
        })
        print(f"    Found {len(results.get('candidates', []))} candidates")
    print()

    # Step 3: AI Validation
    print("Step 3: AI Validation...")
    final_codes = validate_with_ai(raw_note, search_artifacts)
    print(f"Final result: {final_codes}")

def clean_medical_note(raw_text: str) -> List[str]:
    """Step 1: Clean and extract diagnoses from raw text."""
    try:
        from skills.inputCleaner.run import execute as clean_execute
        result = clean_execute(raw_text)
        return result.get("diagnoses", [])
    except Exception as e:
        print(f"Error in cleaning: {e}")
        # Fallback: simple split
        return [d.strip() for d in raw_text.replace(',', ';').split(';') if d.strip()]

def search_icd11(search_term: str) -> Dict[str, Any]:
    """Step 2: Search ICD-11 database."""
    try:
        from skills.icdSearcher.run import execute
        return execute(search_term)
    except Exception as e:
        print(f"Error searching ICD-11: {e}")
        return {"candidates": []}

def validate_with_ai(original_note: str, search_artifacts: List[Dict]) -> str:
    """Step 3: AI validation of results."""
    try:
        from skills.medical_validator.run import execute as validate_execute
        result = validate_execute(original_note, search_artifacts)

        if result.get("result") == "Codes assigned":
            codes = result.get("codes", [])
            if codes:
                return " | ".join([f"{c['code']}: {c['title']} (confidence: {c['confidence']})" for c in codes])

        return result.get("result", "Manual review needed")
    except Exception as e:
        print(f"Error in validation: {e}")
        return "Manual review needed"

if __name__ == "__main__":
    main()