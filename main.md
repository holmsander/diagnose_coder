# MISSION: Medical Code Transformation

## Step 1: Cleaning
Call `note_cleaner` skill with the raw input. 
Output: `diagnosis_list` (Array of strings)

## Step 2: Parallel Search
FOR EACH `item` IN `diagnosis_list`:
    Call `icd_searcher` skill with `search_term` = `item`.
    Collect results into `search_artifacts`.

## Step 3: Validation (The Doctor AI)
Call `medical_validator` skill.
Input: 
  - Original Note
  - `search_artifacts`
Logic: Compare definitions to the note. 
Output: Final ICD codes or "Manual check needed".