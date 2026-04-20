"""
First draft: map doctor diagnosis notes to likely ICD-11 MMS codes
using the official WHO ICD API.

Before running:
1. Register at https://icd.who.int/icdapi and obtain:
   - ICD_CLIENT_ID
   - ICD_CLIENT_SECRET

2. Set environment variables:
   export ICD_CLIENT_ID="..."
   export ICD_CLIENT_SECRET="..."

3. Install:
   pip install requests rapidfuzz

Notes:
- This is a retrieval + reranking baseline, not a production-grade coder.
- Clinical coding usually still needs human review.
- Endpoint paths may evolve; keep them configurable.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

import requests
from rapidfuzz import fuzz


TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
API_BASE = "https://id.who.int/icd/release/11/2026-01/mms"
API_VERSION = "v2"
LANGUAGE = "en"


@dataclass
class ICDCandidate:
    code: Optional[str]
    title: str
    entity_id: Optional[str]
    source_url: Optional[str]
    score: float


class ICDAPIError(RuntimeError):
    pass


class ICD11Client:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        release: str = "2026-01",
        language: str = "en",
        timeout: int = 20,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.release = release
        self.language = language
        self.timeout = timeout

        self.api_base = f"https://id.who.int/icd/release/11/{release}/mms"
        self._token: Optional[str] = None
        self._token_expiry_epoch: float = 0.0

    def _get_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expiry_epoch - 60:
            return self._token

        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "icdapi_access",
            },
            timeout=self.timeout,
        )
        if not resp.ok:
            raise ICDAPIError(
                f"Token request failed: {resp.status_code} {resp.text}"
            )

        data = resp.json()
        access_token = data.get("access_token")
        expires_in = int(data.get("expires_in", 3600))
        if not access_token:
            raise ICDAPIError("Token response did not contain access_token.")

        self._token = access_token
        self._token_expiry_epoch = now + expires_in
        return self._token

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Accept": "application/json",
            "Accept-Language": self.language,
            "API-Version": API_VERSION,
        }

    def search(self, query: str, limit: int = 10, use_flexisearch: bool = True) -> Dict[str, Any]:
        """
        Search ICD-11 MMS. WHO's API supports richer search behavior in v2.
        Parameters can vary by release, so keep this wrapper easy to adjust.
        """
        url = f"{self.api_base}/search"
        params = {
            "q": query,
            "limit": limit,
            "useFlexisearch": str(use_flexisearch).lower(),
            # Often useful if supported by your target API version:
            # "flatResults": "true",
        }

        resp = requests.get(
            url,
            headers=self._headers(),
            params=params,
            timeout=self.timeout,
        )

        if not resp.ok:
            raise ICDAPIError(
                f"Search failed for query={query!r}: {resp.status_code} {resp.text}"
            )

        return resp.json()

    def get_entity(self, entity_path_or_url: str) -> Dict[str, Any]:
        """
        Fetch a specific entity. Accepts either:
        - a full WHO URL
        - or a trailing entity path/id
        """
        if entity_path_or_url.startswith("http://") or entity_path_or_url.startswith("https://"):
            url = entity_path_or_url.replace("http://", "https://")
        else:
            url = f"{self.api_base}/{entity_path_or_url}"

        resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
        if not resp.ok:
            raise ICDAPIError(
                f"Entity lookup failed: {resp.status_code} {resp.text}"
            )
        return resp.json()


def normalize_text(text: str) -> str:
    text = text.strip().lower()
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    # Very small starter set. Expand this over time.
    replacements = {
        "htn": "hypertension",
        "dm2": "type 2 diabetes mellitus",
        "dm ii": "type 2 diabetes mellitus",
        "copd": "chronic obstructive pulmonary disease",
        "mi": "myocardial infarction",
        "uti": "urinary tract infection",
        "ckd": "chronic kidney disease",
    }
    for src, dst in replacements.items():
        text = re.sub(rf"\b{re.escape(src)}\b", dst, text)

    return text


def extract_negation(text: str) -> bool:
    """
    Extremely naive negation detector.
    In production, use a proper clinical NLP negation component.
    """
    negation_patterns = [
        r"\bno evidence of\b",
        r"\brule out\b",
        r"\br/o\b",
        r"\bdenies\b",
        r"\bwithout\b",
        r"\bnot\b",
    ]
    return any(re.search(p, text.lower()) for p in negation_patterns)


def candidate_title(raw_item: Dict[str, Any]) -> str:
    # Search result shape can vary. Try several common keys.
    for key in ("title", "label"):
        val = raw_item.get(key)
        if isinstance(val, str):
            return val
        if isinstance(val, dict) and "@value" in val:
            return val["@value"]

    # Fallbacks
    if "theCodeTitle" in raw_item:
        return str(raw_item["theCodeTitle"])
    return ""


def candidate_code(raw_item: Dict[str, Any]) -> Optional[str]:
    for key in ("code", "theCode"):
        val = raw_item.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return None


def candidate_entity_id(raw_item: Dict[str, Any]) -> Optional[str]:
    for key in ("id", "@id", "destinationEntity", "source"):
        val = raw_item.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return None


def lexical_score(query: str, title: str) -> float:
    if not title:
        return 0.0

    q = query.lower()
    t = title.lower()

    # Blend a few cheap text scores
    return (
        0.45 * fuzz.token_sort_ratio(q, t)
        + 0.35 * fuzz.token_set_ratio(q, t)
        + 0.20 * fuzz.partial_ratio(q, t)
    ) / 100.0


def rerank_candidates(
    query: str,
    raw_results: List[Dict[str, Any]],
    threshold: float = 0.35,
) -> List[ICDCandidate]:
    out: List[ICDCandidate] = []

    for item in raw_results:
        title = candidate_title(item)
        code = candidate_code(item)
        entity_id = candidate_entity_id(item)

        score = lexical_score(query, title)

        # Small bonuses
        if code:
            score += 0.05
        if query.lower() in title.lower():
            score += 0.10

        if score >= threshold:
            out.append(
                ICDCandidate(
                    code=code,
                    title=title,
                    entity_id=entity_id,
                    source_url=entity_id,
                    score=round(min(score, 1.0), 4),
                )
            )

    out.sort(key=lambda x: x.score, reverse=True)
    return out


def pick_items_from_search_response(search_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Different API versions / modes can return slightly different shapes.
    """
    for key in ("destinationEntities", "results", "items"):
        val = search_json.get(key)
        if isinstance(val, list):
            return val
    return []


def map_diagnosis_to_icd11(
    diagnosis: str,
    client: ICD11Client,
    top_k: int = 5,
    threshold: float = 0.35,
) -> Dict[str, Any]:
    original = diagnosis
    normalized = normalize_text(diagnosis)

    # Guardrail: if the note is likely negated, flag it instead of coding it directly.
    is_negated = extract_negation(normalized)

    if is_negated:
        return {
            "input": original,
            "normalized": normalized,
            "negation_flag": True,
            "candidates": [],
            "note": "Possible negation detected; needs human review before coding.",
        }

    # First pass: direct search
    search_json = client.search(normalized, limit=15, use_flexisearch=True)
    raw_items = pick_items_from_search_response(search_json)
    candidates = rerank_candidates(normalized, raw_items, threshold=threshold)

    # Fallback: if too few hits, try a simplified query
    if len(candidates) < 2:
        simplified = re.sub(r"[^a-zA-Z0-9\s]", " ", normalized)
        simplified = re.sub(r"\s+", " ", simplified).strip()
        if simplified and simplified != normalized:
            search_json_2 = client.search(simplified, limit=15, use_flexisearch=True)
            raw_items_2 = pick_items_from_search_response(search_json_2)
            more = rerank_candidates(simplified, raw_items_2, threshold=threshold)

            # Deduplicate by code/title
            seen = {(c.code, c.title) for c in candidates}
            for c in more:
                key = (c.code, c.title)
                if key not in seen:
                    candidates.append(c)
                    seen.add(key)

            candidates.sort(key=lambda x: x.score, reverse=True)

    return {
        "input": original,
        "normalized": normalized,
        "negation_flag": False,
        "candidates": [asdict(c) for c in candidates[:top_k]],
    }


def batch_map_diagnoses(
    diagnoses: List[str],
    client: ICD11Client,
    top_k: int = 5,
    threshold: float = 0.35,
) -> List[Dict[str, Any]]:
    results = []
    for dx in diagnoses:
        try:
            results.append(
                map_diagnosis_to_icd11(
                    diagnosis=dx,
                    client=client,
                    top_k=top_k,
                    threshold=threshold,
                )
            )
        except Exception as e:
            results.append(
                {
                    "input": dx,
                    "error": str(e),
                    "candidates": [],
                }
            )
    return results


if __name__ == "__main__":
    load_dotenv()
    client_id = os.environ.get("ICD_CLIENT_ID")
    client_secret = os.environ.get("ICD_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise SystemExit(
            "Missing ICD_CLIENT_ID / ICD_CLIENT_SECRET environment variables."
        )

    client = ICD11Client(
        client_id=client_id,
        client_secret=client_secret,
        release="2026-01",
        language="en",
    )

    diagnoses = [
        "Essential hypertension",
        "Type 2 diabetes mellitus with diabetic nephropathy",
        "COPD exacerbation",
        "Rule out pneumonia",
        "Acute myocardial infarction",
    ]

    results = batch_map_diagnoses(diagnoses, client, top_k=5, threshold=0.3)

    import json
    print(json.dumps(results, indent=2, ensure_ascii=False))