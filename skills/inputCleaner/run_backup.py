#!/usr/bin/env python3
"""
Input Cleaner Skill - Extract clean diagnoses from sloppy doctor notes using AI
"""

import os
import re
from typing import List, Dict, Any
import ollama

def clean_medical_note_with_ai(raw_text: str) -> List[str]:
    """Use Ollama AI to clean and extract diagnoses from medical notes."""

    prompt = f"""
You are a medical NLP specialist. Your task is to process sloppy clinical notes into clean, discrete diagnostic entities.

INPUT: "{raw_text}"

TASK:
1. Fix all typos and expand medical abbreviations (e.g., "HTN" -> "Hypertension")
2. Group related descriptors into single entities. Do NOT split a single diagnosis into individual words.
   - WRONG: ["Chest", "Pain", "Upper"]
   - RIGHT: ["Upper chest pain"]
3. Standardize terms for high-quality database retrieval
4. If input is unintelligible, return empty list

OUTPUT: Return ONLY a JSON array of strings, like: ["diagnosis one", "diagnosis two"]

Examples:
Input: "Pt has SOB and sharp chest pain upper, plus hx of DM2."
Output: ["shortness of breath", "upper chest pain", "type 2 diabetes mellitus"]

Input: "Patient with htn, dm, and copd exacerbation"
Output: ["hypertension", "diabetes mellitus", "copd exacerbation"]
"""

    try:
        response = ollama.generate(
            model='llama3.1:8b',  # or any available model
            prompt=prompt,
            options={
                'temperature': 0.1,  # Low temperature for consistent output
                'top_p': 0.9,
                'num_predict': 200   # Limit response length
            }
        )

        result_text = response['response'].strip()

        # Try to extract JSON array from response
        import json

        # Look for JSON array in the response
        start_idx = result_text.find('[')
        end_idx = result_text.rfind(']') + 1

        if start_idx != -1 and end_idx > start_idx:
            json_str = result_text[start_idx:end_idx]
            try:
                diagnoses = json.loads(json_str)
                if isinstance(diagnoses, list) and all(isinstance(d, str) for d in diagnoses):
                    return diagnoses
            except json.JSONDecodeError:
                pass

        # Fallback: try to extract diagnoses from text
        lines = result_text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('[') and line.endswith(']'):
                try:
                    diagnoses = json.loads(line)
                    if isinstance(diagnoses, list):
                        return diagnoses
                except:
                    pass

        # Last resort: split by commas and clean up
        diagnoses = [d.strip().strip('"').strip("'") for d in result_text.split(',')]
        diagnoses = [d for d in diagnoses if d and len(d) > 2]  # Filter out empty/short items

        return diagnoses[:5]  # Limit to 5 diagnoses

    except Exception as e:
        print(f"AI cleaning failed: {e}")
        # Return empty list to indicate manual review needed
        return []

def clean_medical_note_fallback(raw_text: str) -> List[str]:
    """Fallback rule-based cleaner when AI fails."""
    # Simple rule-based cleaner (you can enhance with AI later)
    def normalize_medical_text(text: str) -> str:
        """Basic text normalization for medical terms."""
        text = text.lower().strip()

        # Common abbreviations
        replacements = {
            'pt': 'patient',
            'hx': 'history',
            'dm2': 'type 2 diabetes mellitus',
            'dm ii': 'type 2 diabetes mellitus',
            'htn': 'hypertension',
            'sob': 'shortness of breath',
            'cp': 'chest pain',
            'mi': 'myocardial infarction',
            'cad': 'coronary artery disease',
            'copd': 'chronic obstructive pulmonary disease',
            'uti': 'urinary tract infection',
            'ckd': 'chronic kidney disease',
        }

        for abbr, full in replacements.items():
            text = re.sub(rf'\b{re.escape(abbr)}\b', full, text)

        return text

    def extract_diagnoses(text: str) -> List[str]:
        """Extract diagnosis-like phrases from text."""
        # Simple sentence splitting and filtering
        sentences = re.split(r'[.,;]', text)

        diagnoses = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Look for medical terms (very basic)
            medical_indicators = [
                'diabetes', 'hypertension', 'pain', 'infarction', 'disease',
                'syndrome', 'disorder', 'failure', 'infection', 'cancer'
            ]

            if any(indicator in sentence for indicator in medical_indicators):
                diagnoses.append(sentence)

        return diagnoses if diagnoses else [text]  # Fallback to whole text

    normalized = normalize_medical_text(raw_text)
    return extract_diagnoses(normalized)

def execute(raw_text: str) -> Dict[str, Any]:
    """
    Clean raw medical notes into structured diagnosis list using AI.
    This function would be called by the orchestrator.
    """
    if not raw_text or not raw_text.strip():
        return {"diagnoses": []}

    # Try AI cleaning first, fallback to rule-based
    diagnoses = clean_medical_note_with_ai(raw_text)

    return {"diagnoses": diagnoses}

# For testing
if __name__ == "__main__":
    test_note = "Pt has SOB and sharp chest pain upper, plus hx of DM2."
    result = execute(test_note)
    print("Input:", test_note)
    print("Output:", result)