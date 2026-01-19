from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from app.services.normalize import normalize_name
from app.services.path_service import find_path_cached

app = FastAPI(title="Name Related Searching API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class FindPathRequest(BaseModel):
    from_name: str
    to_name: str


class Person(BaseModel):
    label: str
    qid: str


class FindPathResponse(BaseModel):
    from_person: Optional[Person]
    to_person: Optional[Person]
    path: Optional[List[str]]
    message: Optional[str] = None


@app.post("/find-path", response_model=FindPathResponse)
def find_path_api(body: FindPathRequest):
    from_candidates = normalize_name(body.from_name)
    to_candidates = normalize_name(body.to_name)

    if not from_candidates or not to_candidates:
        return FindPathResponse(
            from_person=None,
            to_person=None,
            path=None,
            message="No candidates found from Wikidata",
        )

    for f in from_candidates:
        for t in to_candidates:
            path = find_path_cached(
                start_qid=f["qid"],
                target_qid=t["qid"],
                max_depth=3,
            )
            if path:
                return FindPathResponse(
                    from_person=Person(label=f["label"], qid=f["qid"]),
                    to_person=Person(label=t["label"], qid=t["qid"]),
                    path=path,
                )

    return FindPathResponse(
        from_person=Person(
            label=from_candidates[0]["label"],
            qid=from_candidates[0]["qid"],
        ),
        to_person=Person(
            label=to_candidates[0]["label"],
            qid=to_candidates[0]["qid"],
        ),
        path=None,
        message="No connection found",
    )
