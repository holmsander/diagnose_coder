# Medical Diagnosis Coder

Given a diagnose log written by a doctor, this system converts human-written medical notes into standardized ICD-11 codes.

## Features

- **Input Cleaning**: Extracts and normalizes medical diagnoses from sloppy doctor notes
- **ICD-11 Search**: Searches official WHO ICD-11 database for matching codes
- **AI Validation**: Validates codes against original notes for accuracy

## Local Setup (No External Frameworks Required)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get ICD-11 API Credentials
1. Register at https://icd.who.int/icdapi
2. Get your `ICD_CLIENT_ID` and `ICD_CLIENT_SECRET`

### 3. Create Environment File
Create a `.env` file in the project root:
```
ICD_CLIENT_ID=your_client_id_here
ICD_CLIENT_SECRET=your_client_secret_here
```

### 4. Run the System
```bash
python main.py
```

Enter a doctor note when prompted, and the system will:
1. Clean and extract diagnoses
2. Search ICD-11 for each diagnosis
3. Validate results and return final codes

## Project Structure

```
diagnose_coder/
├── main.py                 # Local orchestrator (replaces Antigravity)
├── main.md                 # Pipeline documentation
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── .env                   # API credentials (create this)
├── skills/
│   ├── inputCleaner/      # Step 1: Clean raw notes
│   │   ├── run.py        # Implementation
│   │   └── responseSchema.py  # Type definitions
│   ├── icdSearcher/      # Step 2: Search ICD-11
│   │   ├── run.py        # Implementation
│   │   ├── instructions.md   # Documentation
│   │   └── responseSchema.py  # Type definitions
│   └── medical_validator/ # Step 3: AI validation
│       └── run.py        # Implementation
└── utils/
    └── icdClient.py      # ICD-11 API client
```

## Architecture

The system follows a 3-step pipeline:

1. **Input Cleaning**: `skills/inputCleaner/run.py`
   - Normalizes medical abbreviations (HTN → hypertension)
   - Extracts discrete diagnosis terms
   - Groups related symptoms

2. **ICD-11 Search**: `skills/icdSearcher/run.py`
   - Calls WHO ICD-11 API
   - Returns top 3 matching codes with definitions
   - Handles authentication and error recovery

3. **AI Validation**: `skills/medical_validator/run.py`
   - Compares search results against original notes
   - Scores matches by semantic similarity
   - Returns final codes or flags for manual review

## Skills Architecture

Each skill follows a consistent pattern:
- `run.py`: Contains `execute()` function called by orchestrator
- `responseSchema.py`: Defines expected input/output types
- `instructions.md`: Human-readable documentation (for icdSearcher)

This makes skills modular, testable, and framework-agnostic.

