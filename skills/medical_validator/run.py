#!/usr/bin/env python3
"""
Medical Validator Skill - AI-powered validation of ICD codes against original notes
"""

import os
from typing import List, Dict, Any
import ollama

def validate_with_ai(original_note: str, search_artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Use Ollama AI to validate ICD codes against original medical notes."""

    if not search_artifacts:
        return {"result": "Manual review needed", "reason": "No search results provided"}

    # Prepare context for AI
    context = f"Original medical note: {original_note}\n\n"
    context += "ICD-11 search results:\n"

    for i, artifact in enumerate(search_artifacts, 1):
        diagnosis = artifact.get('diagnosis', '')
        results = artifact.get('results', {})
        candidates = results.get('candidates', [])

        context += f"\n{i}. Searched for: {diagnosis}\n"
        for j, candidate in enumerate(candidates[:3], 1):  # Top 3 candidates
            code = candidate.get('code', 'Unknown')
            title = candidate.get('title', 'Unknown')
            definition = candidate.get('definition', 'No definition available')
            context += f"   {j}. {code}: {title}\n      Definition: {definition}\n"

    prompt = f"""
You are a medical coding specialist. Your task is to validate ICD-11 codes against the original doctor's note and determine which codes are appropriate.

{context}

VALIDATION TASK:
1. Compare each ICD code's title and definition against the original medical note
2. Determine if the code accurately represents a diagnosis mentioned in the note
3. Consider semantic meaning, not just keyword matching
4. Be conservative - only assign codes that clearly match the clinical description

OUTPUT FORMAT: Return ONLY a JSON object with this exact structure:
{{
    "result": "Codes assigned" or "Manual review needed",
    "codes": [
        {{
            "code": "ICD_CODE",
            "title": "OFFICIAL_TITLE",
            "confidence": "high/medium/low",
            "reason": "Brief explanation of why this code matches"
        }}
    ],
    "notes": "Any additional observations"
}}

CRITERIA:
- "high" confidence: Code directly matches clinical description
- "medium" confidence: Code reasonably matches with some interpretation
- "low" confidence: Code is a stretch, needs human review
- If no codes match well, return "Manual review needed"

Be precise and clinically accurate in your assessment.
"""

    try:
        response = ollama.generate(
            model='llama3.1:8b',
            prompt=prompt,
            options={
                'temperature': 0.2,  # Low temperature for consistent medical decisions
                'top_p': 0.9,
                'num_predict': 500  # Allow longer response for detailed analysis
            }
        )

        result_text = response['response'].strip()

        # Try to extract JSON from response
        import json

        # Look for JSON object in the response
        start_idx = result_text.find('{')
        end_idx = result_text.rfind('}') + 1

        if start_idx != -1 and end_idx > start_idx:
            json_str = result_text[start_idx:end_idx]
            try:
                result = json.loads(json_str)
                # Validate structure
                if isinstance(result, dict) and 'result' in result:
                    return result
            except json.JSONDecodeError:
                pass

        # Fallback: try to find JSON on any line
        lines = result_text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                try:
                    result = json.loads(line)
                    if isinstance(result, dict) and 'result' in result:
                        return result
                except:
                    pass

        # Last resort: algorithmic fallback
        print(f"AI validation failed to parse JSON: {result_text[:200]}...")
        return validate_algorithmic_fallback(original_note, search_artifacts)

    except Exception as e:
        print(f"AI validation failed: {e}")
        return validate_algorithmic_fallback(original_note, search_artifacts)

def validate_algorithmic_fallback(original_note: str, search_artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fallback algorithmic validation when AI fails."""
    def calculate_match_score(original_note: str, candidate: Dict[str, Any]) -> float:
        """Calculate how well a candidate matches the original note."""
        note_lower = original_note.lower()
        title_lower = candidate.get('title', '').lower()
        definition_lower = candidate.get('definition', '').lower()

        # Simple text overlap scoring
        score = 0.0

        # Title matches
        title_words = set(title_lower.split())
        note_words = set(note_lower.split())
        overlap = len(title_words.intersection(note_words))
        if overlap > 0:
            score += 0.4 * (overlap / len(title_words))

        # Definition matches (if available)
        if definition_lower:
            def_words = set(definition_lower.split())
            def_overlap = len(def_words.intersection(note_words))
            if def_overlap > 0:
                score += 0.3 * (def_overlap / len(def_words))

        # Exact phrase matches get bonus
        if title_lower in note_lower:
            score += 0.3

        return min(score, 1.0)

    # Select best candidates
    all_candidates = []

    for artifact in search_artifacts:
        diagnosis = artifact.get('diagnosis', '')
        results = artifact.get('results', {})
        candidates = results.get('candidates', [])

        for candidate in candidates:
            score = calculate_match_score(original_note, candidate)
            all_candidates.append({
                'diagnosis': diagnosis,
                'candidate': candidate,
                'match_score': score
            })

    # Sort by match score and return top candidates
    all_candidates.sort(key=lambda x: x['match_score'], reverse=True)

    # Group by diagnosis and take best per diagnosis
    best_per_diagnosis = {}
    for item in all_candidates:
        diag = item['diagnosis']
        if diag not in best_per_diagnosis or item['match_score'] > best_per_diagnosis[diag]['match_score']:
            best_per_diagnosis[diag] = item

    best_matches = list(best_per_diagnosis.values())

    if not best_matches:
        return {"result": "Manual review needed", "reason": "No suitable matches found"}

    # For now, return all matches above threshold
    threshold = 0.3
    valid_matches = [m for m in best_matches if m['match_score'] >= threshold]

    if not valid_matches:
        return {"result": "Manual review needed", "reason": "No matches above confidence threshold"}

    # Format final result
    final_codes = []
    for match in valid_matches:
        candidate = match['candidate']
        code = candidate.get('code', 'Unknown')
        title = candidate.get('title', 'Unknown')
        confidence = "medium" if match['match_score'] > 0.5 else "low"

        final_codes.append({
            "code": code,
            "title": title,
            "confidence": confidence,
            "reason": f"Algorithmic match score: {match['match_score']:.2f}"
        })

    return {
        "result": "Codes assigned",
        "codes": final_codes
    }

def execute(original_note: str, search_artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate ICD search results against original medical note using AI.
    This function would be called by the orchestrator.
    """
    return validate_with_ai(original_note, search_artifacts)

# For testing
if __name__ == "__main__":
    # Mock data for testing
    original_note = "Patient has shortness of breath and chest pain, history of type 2 diabetes"

    search_artifacts = [
        {
            "diagnosis": "shortness of breath",
            "results": {
                "candidates": [
                    {"code": "R06.0", "title": "Dyspnoea", "definition": "Difficulty breathing"},
                    {"code": "J44.9", "title": "COPD", "definition": "Chronic obstructive pulmonary disease"}
                ]
            }
        },
        {
            "diagnosis": "type 2 diabetes",
            "results": {
                "candidates": [
                    {"code": "E11.9", "title": "Type 2 diabetes mellitus", "definition": "Diabetes mellitus type 2"}
                ]
            }
        }
    ]

    result = execute(original_note, search_artifacts)
    print("Validation Result:")
    print(result)