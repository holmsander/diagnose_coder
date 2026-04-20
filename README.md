# diagnose_coder
Given a diagnose log written by a docter it takes the whumanly written code, converts it to a format that matches ICD11 standards (official diagnose to code system), does a ICD11 search via their official API, gets most plausible results, lets a medicine specialiced LLM compare original notes with the description matching with returned codes, selects best and returns, if none is good enough it marks journal note as incomprehensible for human and returned for some human to manually finish.

