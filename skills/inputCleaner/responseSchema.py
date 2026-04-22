import google.generativeai as genai
import typing_extensions as typing

# 1. Define the Schema for the Skill's output
class DiagnosisList(typing.TypedDict):
    diagnoses: list[str]

# 2. Configure Gemini
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", # Use Flash for speed/low cost on this task
    system_instruction="Extract clean, grouped diagnostic terms from medical notes. Fix typos and abbreviations."
)

# 3. The "Skill" Function
def clean_medical_note(raw_text: str):
    prompt = f"Process this note: {raw_text}"
    
    # Request structured output
    result = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=DiagnosisList
        )
    )
    return result.text

# --- Example Usage ---
sloppy_input = "Pt has SOB and sharp chest pain upper, plus hx of DM2."
cleaned_output = clean_medical_note(sloppy_input)
print(cleaned_output)