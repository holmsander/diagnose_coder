import typing_extensions as typing

class ICDCandidate(typing.TypedDict):
    code: str
    title: str
    definition: str
    foundation_uri: str

class SearchResults(typing.TypedDict):
    candidates: list[ICDCandidate]