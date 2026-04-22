# skills/icd_searcher/run.py
from utils.icdClient import ICD11Client, map_diagnosis_to_icd11
import os

# Initialize the client (usually done once or passed via state)
client = ICD11Client(
    client_id=os.getenv("ICD_CLIENT_ID"),
    client_secret=os.getenv("ICD_CLIENT_SECRET")
)

def execute(search_term: str):
    """
    This is the function Antigravity calls.
    It bridges the AI's request to your Python script.
    """
    # We use your script's logic here!
    result = map_diagnosis_to_icd11(search_term, client)
    
    # Return the candidates in the format your schema expects
    return result