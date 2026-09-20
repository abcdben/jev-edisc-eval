"""TREC 2016 Total Recall (athome4) on the Jeb Bush email collection.

Sources (NIST, https://trec.nist.gov/data/total-recall/):
  data/trec/raw/tr2016-ext-topics.txt    topic, title -- description (34 topics)
  data/trec/raw/athome4.facetsandqrels   topic docno rel subtopic; rel 0=nonrel 1=rel 2=important
  data/trec/raw/prels.tr2016.alt{1,2,3}  alternate-assessor samples (inter-assessor ceiling)
  data/trec/raw/athome1/                 the 2015 ten topics (complete judgments) for the full-collection tier
  TREC/Jeb Bush TXT/<docno>.txt          290,099 emails (user-supplied copy of the collection)

Gold: rel in {1,2} -> responsive; judged-nonrelevant and unjudged -> not responsive (TREC convention).
`important` (rel=2) and the subtopic code are kept in meta so recall on key documents and facet
coverage can be reported. No gray flags: NIST's labels are used as-is.

Three sample files are produced:
  dev.jsonl    ~60/topic for prompt iteration: positives spread over subtopic facets, hard negatives
               one per TF-IDF cluster. Never evaluated on.
  eval.jsonl   ~3,000 stratified: up to N_POS gold positives per topic, hard negatives, random emails
               at natural prevalence. Excludes dev and any doc ids listed in data/trec/seen_ids.txt
               (documents the analyst read while exploring the collection).
  full.jsonl   every email <= MAX_CHARS, labeled on the 12 topics (+ the 2015 ten), minus dev/seen.
"""

from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

RAW = Path("data/trec/raw")
COLL = Path("TREC/Jeb Bush TXT")
MAX_CHARS = 12000  # ~3k tokens; longer emails are excluded (same rule as Mallinckrodt)

TOPICS_2016 = {  # topic -> question id
    "415": "gw_bush",
    "417": "movie_gallery",
    "419": "rilya_wilson",
    "407": "faith_based",
    "416": "marketing",
    "412": "recount_2000",
    "410": "condominiums",
    "403": "bottled_water",
    "414": "medicaid_reform",
    "404": "eminent_domain",
    "423": "nra_rifle",
    "422": "nra_aliens",
}
# (topic, facet) pairs whose gold contradicts the topic's own text. Kept as gold-positive (NIST's
# label stands) but flagged gray so metrics can be reported with and without them.
#   423/154: the "NRA issue" letters from Florida bankers about the IRS non-resident-alien interest
#            reporting rule, judged relevant (mostly "important") to the National Rifle Association
#            topic, which states "Documents concerning the non-resident alien issue are not relevant."
GOLD_CONFLICT = {("423", "154")}

TOPICS_2015 = {
    "athome100": "a1_school_funding",
    "athome101": "a1_judicial_selection",
    "athome102": "a1_capital_punishment",
    "athome103": "a1_manatee_protection",
    "athome104": "a1_medical_schools",
    "athome105": "a1_affirmative_action",
    "athome106": "a1_terri_schiavo",
    "athome107": "a1_tort_reform",
    "athome108": "a1_manatee_county",
    "athome109": "a1_scarlet_letter",
}


def load_topics() -> dict[str, tuple[str, str]]:
    out = {}
    for l in (RAW / "tr2016-ext-topics.txt").read_text().splitlines():
        if not l.strip():
            continue
        num, rest = l.split(maxsplit=1)
        title, desc = rest.split(" -- ", 1)
        out[num] = (title.strip(), re.sub(r"\s+", " ", desc).strip())
    return out


def load_qrels():
    """Returns rel[topic][docno]=grade(1|2), nonrel[topic]=set(docno), facet[(topic,docno)]=code."""
    rel: dict[str, dict[str, int]] = defaultdict(dict)
    nonrel: dict[str, set[str]] = defaultdict(set)
    facet: dict[tuple[str, str], str] = {}
    for l in (RAW / "athome4.facetsandqrels").read_text().splitlines():
        p = l.split()
        if len(p) < 4:
            continue
        t, d, r, f = p[:4]
        d = str(int(d))
        if r in ("1", "2"):
            rel[t][d] = int(r)
            facet[(t, d)] = f
        else:
            nonrel[t].add(d)
    return rel, nonrel, facet


def load_qrels_2015() -> dict[str, set[str]]:
    out = {}
    for t in TOPICS_2015:
        ids = set()
        for l in (RAW / "athome1" / f"judgments_{t}").read_text().splitlines():
            p = l.split()
            if p and p[0] != "docid":
                ids.add(str(int(p[0].split("-")[1])))
        out[t] = ids
    return out


def read_email(docno: str) -> str:
    p = COLL / f"{int(docno)}.txt"
    b = p.read_bytes()
    try:
        t = b.decode("utf-8")
    except UnicodeDecodeError:
        t = b.decode("latin-1")
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def all_docnos() -> list[str]:
    return sorted((p.stem for p in COLL.glob("*.txt") if p.stem.isdigit()), key=int)


def make_doc(docno: str, text: str, rel, facet, rel15) -> dict:
    labels = {}
    meta: dict = {"docno": docno, "n_chars": len(text), "important": [], "facet": {}}
    gray: list[str] = []
    for t, q in TOPICS_2016.items():
        g = rel[t].get(docno)
        if g:
            labels[q] = "responsive"
            meta["facet"][q] = facet.get((t, docno))
            if g == 2:
                meta["important"].append(q)
            if (t, facet.get((t, docno))) in GOLD_CONFLICT:
                gray.append(q)
    for t, q in TOPICS_2015.items():
        if docno in rel15[t]:
            labels[q] = "responsive"
    return {"id": f"JB-{int(docno):06d}", "text": text, "labels": labels, "gray": gray, "meta": meta}


def _clusters_pick(docnos: list[str], k: int, seed: int) -> list[str]:
    """One representative per TF-IDF k-means cluster (closest to centroid)."""
    if k <= 0:
        return []
    if len(docnos) <= k:
        return list(docnos)
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer

    texts = [read_email(d)[:6000] for d in docnos]
    X = TfidfVectorizer(max_features=20000, stop_words="english", sublinear_tf=True, min_df=2).fit_transform(texts)
    km = KMeans(n_clusters=k, n_init=4, random_state=seed).fit(X)
    picks = []
    for c in range(k):
        idx = np.where(km.labels_ == c)[0]
        if len(idx) == 0:
            continue
        diff = np.asarray(X[idx].todense()) - km.cluster_centers_[c]
        dist = (diff * diff).sum(axis=1)
        picks.append(docnos[idx[int(dist.argmin())]])
    return picks


def build_dev(out: Path, seen: set[str] | None = None, n_pos: int = 30, n_neg: int = 30, seed: int = 21) -> set[str]:
    """Documents already read during exploration (`seen`) are placed in dev first, since they are
    burned for evaluation anyway. Dev takes at most a third of a topic's positives."""
    seen = seen or set()
    rel, nonrel, facet = load_qrels()
    rel15 = load_qrels_2015()
    rng = random.Random(seed)
    chosen: dict[str, dict] = {}
    for t in TOPICS_2016:
        pos = [d for d in sorted(rel[t], key=int) if len(read_email(d)) <= MAX_CHARS]
        cap = min(n_pos, max(3, len(pos) // 3))
        picks: list[str] = [d for d in pos if d in seen][:cap]
        # spread remaining positives across subtopic facets: round-robin over facets, random within
        by_f: dict[str, list[str]] = defaultdict(list)
        for d in pos:
            if d not in picks:
                by_f[facet[(t, d)]].append(d)
        for lst in by_f.values():
            rng.shuffle(lst)
        while len(picks) < cap and any(by_f.values()):
            for f in sorted(by_f, key=lambda f: -len(by_f[f])):
                if by_f[f] and len(picks) < cap:
                    picks.append(by_f[f].pop())
        neg = [d for d in sorted(nonrel[t], key=int) if len(read_email(d)) <= MAX_CHARS and d not in rel[t]]
        neg_seen = [d for d in neg if d in seen]
        neg = neg_seen + [d for d in neg if d not in seen]
        rest = neg[len(neg_seen):]
        rng.shuffle(rest)
        neg_picks = neg_seen + _clusters_pick(rest[:600], max(0, n_neg - len(neg_seen)), seed)
        for d in picks + neg_picks:
            if d not in chosen:
                chosen[d] = make_doc(d, read_email(d), rel, facet, rel15)
                chosen[d]["meta"]["dev_topic"] = t
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(chosen[d]) + "\n" for d in sorted(chosen, key=int)))
    print(f"dev: {len(chosen)} emails -> {out}")
    return set(chosen)


def build_eval(out: Path, exclude: set[str], n_pos: int = 100, n_hard: int = 1000, n_rand: int = 1000, seed: int = 22) -> None:
    rel, nonrel, facet = load_qrels()
    rel15 = load_qrels_2015()
    rng = random.Random(seed)
    chosen: dict[str, dict] = {}
    strata: Counter = Counter()

    def add(d: str, stratum: str) -> bool:
        if d in exclude or d in chosen:
            return False
        text = read_email(d)
        if len(text) > MAX_CHARS:
            return False
        chosen[d] = make_doc(d, text, rel, facet, rel15)
        chosen[d]["meta"]["stratum"] = stratum
        strata[stratum] += 1
        return True

    for t in TOPICS_2016:
        pos = sorted(rel[t])
        rng.shuffle(pos)
        n = 0
        for d in pos:
            if n >= n_pos:
                break
            n += add(d, f"pos:{TOPICS_2016[t]}")
    hard = sorted(set().union(*nonrel.values()) - set().union(*(set(r) for r in rel.values())))
    rng.shuffle(hard)
    n = 0
    for d in hard:
        if n >= n_hard:
            break
        n += add(d, "hard_neg")
    every = all_docnos()
    rng.shuffle(every)
    n = 0
    for d in every:
        if n >= n_rand:
            break
        n += add(d, "random")
    out.write_text("".join(json.dumps(chosen[d]) + "\n" for d in sorted(chosen, key=int)))
    print(f"eval: {len(chosen)} emails -> {out}")
    for k, v in sorted(strata.items()):
        print(f"   {k:<28} {v}")
    pos_counts = Counter(q for d in chosen.values() for q in d["labels"] if not q.startswith("a1_"))
    print("   positives per question:", dict(sorted(pos_counts.items())))


def build_full(out: Path, exclude: set[str]) -> None:
    rel, nonrel, facet = load_qrels()
    rel15 = load_qrels_2015()
    n = skipped = 0
    with out.open("w") as f:
        for d in all_docnos():
            if d in exclude:
                continue
            text = read_email(d)
            if len(text) > MAX_CHARS:
                skipped += 1
                continue
            f.write(json.dumps(make_doc(d, text, rel, facet, rel15)) + "\n")
            n += 1
    print(f"full: {n} emails -> {out} (excluded {len(exclude)} dev/seen, {skipped} over {MAX_CHARS} chars)")
