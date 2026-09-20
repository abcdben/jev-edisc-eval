"""Fetch Mallinckrodt emails (metadata + extracted text) from the UCSF/JHU
Opioid Industry Documents Archive.

Two public endpoints are used:

* Solr metadata index: ``https://metadata.idl.ucsf.edu/solr/ltdl3/select``
  (edismax, ``q.op=AND``, default field ``er`` = "everywhere"). The ``/query``
  handler ignores ``rows``/``fl``/``facet`` and always returns 1000 docs, so
  ``/select`` is used. ``fl`` must use *raw* schema field names (``ti``, ``au``,
  ``rc``, ``dd`` ...); the friendly aliases (``title``, ``author`` ...) only
  work inside ``q``. See ``FIELD_ALIASES``.
* S3 dataset bucket (no auth): extracted text for doc ``abcd1234`` lives at
  ``a/b/c/d/abcd1234/abcd1234.ocr`` next to the ``.pdf`` / ``.tif`` / thumbnail.

Only stdlib + ``httpx`` (falls back to ``urllib`` if httpx is unavailable).
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterator

try:  # httpx is preferred but optional
    import httpx  # type: ignore
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

SOLR_URL = "https://metadata.idl.ucsf.edu/solr/ltdl3/select"
S3_BASE = "https://opioid-industry-documents-archive-dataset-bucket.s3.amazonaws.com"

EMAIL_BASE_Q = '(collection:"Mallinckrodt Litigation Documents" AND type:email)'

# Friendly alias -> raw Solr field name (raw names are what ``fl`` needs and
# what comes back in result docs; aliases are accepted inside ``q`` only).
FIELD_ALIASES: dict[str, str] = {
    "title": "ti",
    "author": "au",
    "recipient": "rc",
    "copied": "cc",
    "documentdate": "dd",
    "type": "dt",
    "drug": "dg",
    "pages": "pg",
    "bates": "bn",
    "file": "fn",
    "text": "ot",
    "description": "desc",
    "date": "dd",
}

# Convenient default field list for emails (raw names).
EMAIL_FL: list[str] = [
    "id", "ti", "au", "rc", "cc", "dd", "datesent", "timesent", "pg",
    "custodian", "dg", "bn", "filepath", "conversation", "attachment", "originalformat",
]

PAGE_SIZE = 100
PAGE_SLEEP = 0.2
RETRIES = 4
TIMEOUT = 60.0
USER_AGENT = "ediscovery-bench/0.1 (+research; polite crawler)"


class FetchError(RuntimeError):
    pass


# --------------------------------------------------------------------------- HTTP

def _http_get(url: str, params: dict[str, Any] | None = None, *, retries: int = RETRIES,
              timeout: float = TIMEOUT) -> tuple[int, bytes]:
    """GET with retries/backoff. Returns (status, body). 404 is returned, not raised."""
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params, doseq=True)
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            if httpx is not None:
                r = httpx.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT},
                              follow_redirects=True)
                status, body = r.status_code, r.content
            else:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                try:
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        status, body = resp.status, resp.read()
                except urllib.error.HTTPError as e:
                    status, body = e.code, e.read()
            if status == 404:
                return status, body
            if status >= 500 or status == 429 or status == 403:
                # 403 is what the S3 endpoint/solr proxy return when throttling;
                # treat as transient.
                raise FetchError(f"HTTP {status} for {url[:200]}")
            return status, body
        except Exception as e:  # noqa: BLE001 - network errors are transient
            last_exc = e
            time.sleep(min(1.0 * (2 ** attempt), 10.0))
    raise FetchError(f"giving up after {retries} attempts: {last_exc}")


# --------------------------------------------------------------------------- Solr

def _solr(params: dict[str, Any]) -> dict[str, Any]:
    params = {"wt": "json", **params}
    status, body = _http_get(SOLR_URL, params)
    if status != 200:
        raise FetchError(f"Solr HTTP {status}: {body[:300]!r}")
    data = json.loads(body)
    if "error" in data:
        raise FetchError(f"Solr error: {data['error'].get('msg')}")
    return data


def _normalize_fl(fl: list[str]) -> str:
    raw = [FIELD_ALIASES.get(f, f) for f in fl]
    if "id" not in raw:
        raw.insert(0, "id")
    return ",".join(dict.fromkeys(raw))


def solr_search(q: str, fl: list[str], max_rows: int,
                extra_params: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Yield up to ``max_rows`` Solr docs for ``q`` using cursorMark deep paging.

    ``fl`` may use friendly aliases (``title``/``author``/...) or raw names.
    ``extra_params`` may override ``sort`` (must include ``id`` as tiebreaker for
    cursorMark; ``id asc`` is appended automatically if missing), ``fq``, etc.
    """
    if max_rows <= 0:
        return
    extra = dict(extra_params or {})
    sort = extra.pop("sort", "id asc")
    if "id" not in sort:
        sort = f"{sort}, id asc"
    cursor = "*"
    yielded = 0
    while yielded < max_rows:
        rows = min(PAGE_SIZE, max_rows - yielded)
        data = _solr({"q": q, "fl": _normalize_fl(fl), "rows": rows, "sort": sort,
                      "cursorMark": cursor, **extra})
        docs = data["response"]["docs"]
        for d in docs:
            yield d
            yielded += 1
            if yielded >= max_rows:
                return
        next_cursor = data.get("nextCursorMark")
        if not docs or next_cursor is None or next_cursor == cursor:
            return
        cursor = next_cursor
        time.sleep(PAGE_SLEEP)


def solr_count(q: str, extra_params: dict[str, Any] | None = None) -> int:
    data = _solr({"q": q, "rows": 0, **(extra_params or {})})
    return int(data["response"]["numFound"])


def facet(q: str, field: str, limit: int = 80,
          extra_params: dict[str, Any] | None = None) -> list[tuple[str, int]]:
    """Field facet counts. NOTE: in this index only ``*_facet``-style fields and
    a few string fields (``collectioncode``, ``id``) are facetable; ``custodian``,
    ``au``, ``rc`` are analysed text fields and return an empty list (use
    :func:`sample_field_counts` to estimate instead)."""
    data = _solr({"q": q, "rows": 0, "facet": "true", "facet.field": field,
                  "facet.limit": limit, "facet.mincount": 1, **(extra_params or {})})
    flat = data.get("facet_counts", {}).get("facet_fields", {}).get(field, [])
    return [(flat[i], int(flat[i + 1])) for i in range(0, len(flat), 2)]


def sample_field_counts(q: str, field: str, sample_size: int = 5000,
                        seed: int = 7) -> tuple[int, list[tuple[str, int]]]:
    """Estimate value distribution of a non-facetable multivalued field by
    drawing a random sample (Solr ``random_<seed>`` sort, up to 1000 rows per
    request). Returns (n_sampled, [(value, count), ...] sorted desc)."""
    counts: dict[str, int] = {}
    n = 0
    start = 0
    while n < sample_size:
        rows = min(1000, sample_size - n)
        data = _solr({"q": q, "fl": f"id,{field}", "rows": rows, "start": start,
                      "sort": f"random_{seed} asc"})
        docs = data["response"]["docs"]
        if not docs:
            break
        for d in docs:
            n += 1
            vals = d.get(field, [])
            if isinstance(vals, str):
                vals = [vals]
            for v in vals:
                counts[v] = counts.get(v, 0) + 1
        start += len(docs)
        time.sleep(PAGE_SLEEP)
    return n, sorted(counts.items(), key=lambda kv: -kv[1])


# --------------------------------------------------------------------------- S3 text

def text_key(doc_id: str) -> str:
    """S3 key of the extracted (OCR/plain) text for a document id.

    ``hsvn0234`` -> ``h/s/v/n/hsvn0234/hsvn0234.ocr``
    """
    doc_id = doc_id.strip().lower()
    if len(doc_id) < 4:
        raise ValueError(f"bad doc id: {doc_id!r}")
    return f"{doc_id[0]}/{doc_id[1]}/{doc_id[2]}/{doc_id[3]}/{doc_id}/{doc_id}.ocr"


def pdf_key(doc_id: str) -> str:
    return text_key(doc_id)[:-4] + ".pdf"


def fetch_text(doc_id: str) -> str | None:
    """Download extracted text for ``doc_id``; ``None`` if the object is missing."""
    status, body = _http_get(f"{S3_BASE}/{text_key(doc_id)}")
    if status == 404:
        return None
    if status != 200:
        raise FetchError(f"S3 HTTP {status} for {doc_id}")
    # .ocr files start with a UTF-8 BOM; utf-8-sig strips it.
    return body.decode("utf-8-sig", errors="replace")


# --------------------------------------------------------------------------- helpers

def first(v: Any) -> Any:
    """Solr returns most fields as single-element lists; unwrap."""
    if isinstance(v, list):
        return v[0] if v else None
    return v


def email_record(doc: dict[str, Any]) -> dict[str, Any]:
    """Flatten a Solr email doc into a plain dict with friendly names."""
    return {
        "id": doc.get("id"),
        "title": first(doc.get("ti")),
        "author": first(doc.get("au")),
        "recipient": first(doc.get("rc")),
        "copied": first(doc.get("cc")),
        "date": first(doc.get("dd")),
        "datesent": first(doc.get("datesent")),
        "timesent": first(doc.get("timesent")),
        "pages": first(doc.get("pg")),
        "custodian": doc.get("custodian") or [],
        "drug": doc.get("dg") or [],
        "bates": first(doc.get("bn")),
        "filepath": first(doc.get("filepath")),
        "conversation": first(doc.get("conversation")),
        "attachments": doc.get("attachment") or [],
    }


if __name__ == "__main__":  # quick smoke test: 5 emails end-to-end
    for d in solr_search(EMAIL_BASE_Q, EMAIL_FL, 5):
        rec = email_record(d)
        txt = fetch_text(rec["id"])
        print("=" * 80)
        print(f"id={rec['id']} date={rec['date']} pages={rec['pages']} custodian={rec['custodian']}")
        print(f"author={rec['author']}")
        print(f"recipient={rec['recipient']}")
        print(f"title={rec['title']}")
        print(f"text_len={None if txt is None else len(txt)}")
        print((txt or "<no text>")[:300])
