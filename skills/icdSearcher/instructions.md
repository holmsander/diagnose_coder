# ICD-11 Search Skill
This skill takes a single, cleaned medical term and searches the official WHO ICD-11 database.

## Inputs
- `search_term`: A string (e.g., "Type 2 Diabetes Mellitus")

## Behavior
- Perform a GET request to the ICD-11 search endpoint.
- Filter for 'MMS' (Mortality and Morbidity Statistics) linearization.
- Return the top 3 matches including their unique Code, Title, and Foundation URI.