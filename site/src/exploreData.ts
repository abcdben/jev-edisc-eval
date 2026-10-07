/** site/public/explore/, written by `bench export-explore` (ediscovery_bench/explore.py); document text from `bench serve` (local only). */

export type Lab = 1 | 0 | -1; // responsive, not responsive, gray/unjudged
export type Topic = { id: string; key: string; title: string; kind: "responsiveness" | "privilege"; n: number; n_pos: number; n_gray: number; n_contested: number; rfp_text: string | null; note?: string | null };
export type HumanArm = { id: string; name: string; short: string; color: string; note?: string };
/** `meta`: TAR arms only, the simulated reviewer's per-row provenance file (TarMeta) beside the arm's scores. */
export type ModelArm = { id: string; name: string; short: string; kind: string; color: string; planned: boolean; note?: string | null; file: string; coverage?: number | null; meta?: string };
export type Arm = { id: string; name: string; short: string; color: string; human: boolean; planned: boolean; note?: string | null; file?: string; coverage?: number | null; kind?: string; meta?: string };
export type Dataset = {
  id: string; kind: "judgments" | "corpus" | "trec-alt"; label: string; short: string; text: boolean; text_note?: string | null;
  n: number; n_docs: number; n_families: number; has_attachments: boolean; inherit_default: boolean; placeholders: boolean;
  topics: Topic[]; humans: HumanArm[]; arms: ModelArm[]; default: { standard: string; a: string | null; b: string | null; topics: string[] };
};
export type Index = { datasets: Dataset[] };
export type Rows = { n: number; topics: string[]; families: string[]; docid: string[]; topic: number[]; family: number[]; att: number[]; chars: (number | null)[]; psel: (number | null)[]; humans: Record<string, Lab[]> };
export type ArmScores = { arm: string; planned: boolean; p: (number | null)[] };
/**
 * A TAR arm's reviewer provenance (explore.py _tar_meta, tar.py Reviewer.provenance), aligned to rows.json: `src` who made the call (-1 not covered,
 * 0 the classifier, 1 the simulated reviewer); for the reviewer's rows the uniform `u` behind its miscode decision, the document's gold flag `g`
 * (any issue), this row's issue gold `gq`, and `fpq`, the rows.json topic index the reviewer over-coded (-1: none); `default` the run's own rates.
 */
export type TarMeta = { default: { fn: number; fp: number }; src: number[]; u: (number | null)[]; g: number[]; gq: number[]; fpq: number[] };

export const BASE = import.meta.env.BASE_URL.replace(/\/?$/, "/");
export const TEXT_API = (import.meta.env.VITE_TEXT_API as string | undefined) ?? "http://127.0.0.1:8766";

const cache = new Map<string, Promise<unknown>>();
async function getJSON<T>(url: string): Promise<T> {
  if (!cache.has(url)) cache.set(url, fetch(url).then((r) => { if (!r.ok) throw new Error(`${r.status} ${url}`); return r.json(); }));
  return cache.get(url) as Promise<T>;
}
export const loadIndex = () => getJSON<Index>(`${BASE}explore/index.json`);
export const loadRows = (ds: string) => getJSON<Rows>(`${BASE}explore/${ds}/rows.json`);
export const loadArm = (ds: string, file: string) => getJSON<ArmScores>(`${BASE}explore/${ds}/arms/${file}`);
export const loadMeta = (ds: string, file: string) => getJSON<TarMeta>(`${BASE}explore/${ds}/arms/${file}`);

/** The scores a TAR arm's rows carry for a coded label (the arm files write these two values for the reviewer's calls). */
const P_CODED_R = 0.999, P_CODED_NR = 0.001;
/**
 * A TAR arm's scores with the simulated reviewer's rows re-coded under other error rates (`r` null: the shipped scores, the run's own rates).
 * The rule is tar.py Reviewer.code, replayed from the draw each row carries: a gold-positive document is missed (every issue coded not relevant)
 * when u < fn, otherwise coded as its gold; a gold-negative one is over-coded relevant on one issue when u < fp, the issue the run drew (`fpq`)
 * or, for a document the run did not over-code (its rate was lower, so it drew no issue), one taken from the uniform's own digits. The
 * classifier's rows do not change: the model it was trained on, and where the workflow stopped, stay at the default run. At the run's own
 * rates this reproduces the shipped scores exactly. Rows without a draw (a reviewer with both rates at zero never drew) stay as shipped.
 */
export function reviewerScores(rows: Rows, scores: ArmScores, meta: TarMeta, r: { fn: number; fp: number } | null): ArmScores {
  if (!r) return scores;
  const nT = rows.topics.length;
  const p = scores.p.map((v, i) => {
    if (meta.src[i] !== 1) return v;
    const u = meta.u[i];
    if (u == null) return v;
    if (meta.g[i] === 1) return u < r.fn ? P_CODED_NR : meta.gq[i] === 1 ? P_CODED_R : P_CODED_NR;
    if (u >= r.fp) return P_CODED_NR;
    const q = meta.fpq[i] >= 0 ? meta.fpq[i] : Math.round(u * 1e4) % nT;
    return rows.topic[i] === q ? P_CODED_R : P_CODED_NR;
  });
  return { ...scores, p };
}

export type DocText = { docid: string; text: string; meta: Record<string, unknown>; labels: Record<string, string>; gray: string[] };
export const fetchText = (ds: string, docid: string) => getJSON<DocText>(`${TEXT_API}/text/${ds}/${encodeURIComponent(docid)}`);
export const fetchFamily = (ds: string, msgid: string) => getJSON<{ msg_id: string; docs: DocText[] }>(`${TEXT_API}/family/${ds}/${encodeURIComponent(msgid)}`);

export const armsOf = (d: Dataset): Arm[] => [
  ...d.humans.map((h) => ({ ...h, human: true, planned: false })),
  ...d.arms.map((a) => ({ ...a, human: false })),
];

/** Topic name for lists: numbered topics read "301 · Oil and gas drilling", keyed ones just their title. */
export const topicName = (t: Topic) => (/^\d/.test(t.id) ? `${t.id} · ${t.title}` : t.title);

/**
 * The TREC Legal rule applied to a model's scores: a parent email counts as responsive if any of its attachments does, so at document
 * level the parent's p becomes the max over the family (same topic); attachments keep their own. Returns the scores unchanged when the
 * dataset has no attachments.
 */
export function inheritScores(rows: Rows, scores: ArmScores): ArmScores {
  if (!rows.att.some((a) => a)) return scores;
  const best = new Map<string, number>();
  for (let i = 0; i < rows.n; i++) {
    const v = scores.p[i]; if (v == null) continue;
    const k = `${rows.topic[i]}:${rows.family[i]}`;
    const b = best.get(k); if (b == null || v > b) best.set(k, v);
  }
  const p = scores.p.map((v, i) => (rows.att[i] ? v : (best.get(`${rows.topic[i]}:${rows.family[i]}`) ?? v)));
  return { ...scores, p };
}

// ------------------------------------------------------------------------------------------------ units

/** One row of the explorer: a judgment (document x topic), or a family (message + attachments) of them. */
export type Unit = { i: number; ids: number[]; docid: string; family: string; topic: number; att: boolean; chars: number | null; psel: number | null; n: number };

export function unitsOf(rows: Rows, topicIdx: Set<number>, families: boolean): Unit[] {
  const out: Unit[] = [];
  if (!families) {
    for (let i = 0; i < rows.n; i++) {
      if (!topicIdx.has(rows.topic[i])) continue;
      out.push({ i, ids: [i], docid: rows.docid[i], family: rows.families[rows.family[i]], topic: rows.topic[i], att: !!rows.att[i], chars: rows.chars[i], psel: rows.psel[i], n: 1 });
    }
    return out;
  }
  const by = new Map<string, Unit>();
  for (let i = 0; i < rows.n; i++) {
    if (!topicIdx.has(rows.topic[i])) continue;
    const k = `${rows.topic[i]}:${rows.family[i]}`;
    const u = by.get(k);
    if (!u) { by.set(k, { i, ids: [i], docid: rows.families[rows.family[i]], family: rows.families[rows.family[i]], topic: rows.topic[i], att: false, chars: rows.chars[i], psel: rows.psel[i], n: 1 }); continue; }
    u.ids.push(i); u.n++;
    if (rows.chars[i] != null) u.chars = (u.chars ?? 0) + rows.chars[i]!;
    if (!rows.att[i]) { u.i = i; u.psel = rows.psel[i]; }
  }
  return [...by.values()];
}

/** Label of an arm for a unit. Models: p >= threshold; families: responsive if any member is, gray only if every member is. */
export type Labeler = (u: Unit) => Lab;
export type Scorer = (u: Unit) => number | null;

export function labelerFor(arm: Arm, rows: Rows, scores: ArmScores | null, threshold: number): Labeler {
  if (arm.human) {
    const col = rows.humans[arm.id];
    return (u) => {
      if (u.ids.length === 1) return col[u.ids[0]];
      let any = false, allGray = true;
      for (const i of u.ids) { const l = col[i]; if (l === 1) any = true; if (l !== -1) allGray = false; }
      return any ? 1 : allGray ? -1 : 0;
    };
  }
  const p = scores?.p;
  return (u) => {
    if (!p) return -1;
    let best: number | null = null;
    for (const i of u.ids) { const v = p[i]; if (v != null && (best == null || v > best)) best = v; }
    return best == null ? -1 : best >= threshold ? 1 : 0;
  };
}
export function scorerFor(arm: Arm, scores: ArmScores | null): Scorer | null {
  if (arm.human || !scores) return null;
  const p = scores.p;
  return (u) => { let best: number | null = null; for (const i of u.ids) { const v = p[i]; if (v != null && (best == null || v > best)) best = v; } return best; };
}

// ------------------------------------------------------------------------------------------------ buckets

/** How arm A came out against the standard. */
export type Outcome = "agree_r" | "agree_nr" | "miss" | "over" | "gray";
/** Where the overlay B stands inside that outcome. */
export type Side = "agree" | "dissent" | "std" | "a";
export type BucketKey = `${Outcome}` | `${Outcome}.${Side}`;

export const outcomeOf = (s: Lab, a: Lab): Outcome => (s === -1 || a === -1 ? "gray" : s === 1 && a === 1 ? "agree_r" : s === 0 && a === 0 ? "agree_nr" : s === 1 ? "miss" : "over");
export const sideOf = (o: Outcome, s: Lab, b: Lab): Side => (o === "agree_r" || o === "agree_nr" ? (b === s ? "agree" : "dissent") : b === s ? "std" : "a");
export const bucketOf = (s: Lab, a: Lab, b: Lab | null): BucketKey => { const o = outcomeOf(s, a); return o === "gray" || b == null ? o : `${o}.${sideOf(o, s, b)}`; };

export const OUTCOME_ORDER: Outcome[] = ["agree_nr", "over", "miss", "agree_r", "gray"];
export type BucketDef = { key: BucketKey; outcome: Outcome; side: Side | null; group: string; short: string; label: string; bR: boolean | null };

/** The bucket catalogue for a (standard, A, B) choice, with names that say who called what. */
export function bucketDefs(S: string, A: string | null, B: string | null): BucketDef[] {
  if (!A) return [
    { key: "agree_r", outcome: "agree_r", side: null, group: S, short: "Responsive", label: `${S}: responsive`, bR: null },
    { key: "agree_nr", outcome: "agree_nr", side: null, group: S, short: "Not responsive", label: `${S}: not responsive`, bR: null },
    { key: "gray", outcome: "gray", side: null, group: "Unjudged", short: "Gray", label: `Gray or unjudged by ${S}`, bR: null },
  ];
  const O: Record<Outcome, { group: string; label: string; aR: boolean | null }> = {
    agree_r: { group: `${A} and ${S} agree`, label: `${A} and ${S}: responsive`, aR: true },
    agree_nr: { group: `${A} and ${S} agree`, label: `${A} and ${S}: not responsive`, aR: false },
    miss: { group: `${A} disagrees with ${S}`, label: `${A} not responsive, ${S} responsive`, aR: false },
    over: { group: `${A} disagrees with ${S}`, label: `${A} responsive, ${S} not`, aR: true },
    gray: { group: "Unjudged", label: `Gray or unjudged by ${S} or ${A}`, aR: null },
  };
  const out: BucketDef[] = [];
  for (const o of OUTCOME_ORDER) {
    const d = O[o];
    if (!B || o === "gray") { out.push({ key: o, outcome: o, side: null, group: d.group, short: o === "agree_r" ? "Both responsive" : o === "agree_nr" ? "Both not responsive" : o === "miss" ? `${A} missed` : o === "over" ? `${A} over-called` : "Gray", label: d.label, bR: null }); continue; }
    if (o === "agree_r" || o === "agree_nr") {
      out.push({ key: `${o}.agree`, outcome: o, side: "agree", group: d.group, short: o === "agree_r" ? "All responsive" : "All not responsive", label: `${d.label}; ${B} agrees`, bR: d.aR });
      out.push({ key: `${o}.dissent`, outcome: o, side: "dissent", group: d.group, short: o === "agree_r" ? `${B} misses` : `${B} alone`, label: `${d.label}; ${B} ${d.aR ? "not responsive" : "responsive"}`, bR: !d.aR });
    } else {
      const sR = o === "miss";
      out.push({ key: `${o}.std`, outcome: o, side: "std", group: d.group, short: `${o === "miss" ? `${A} missed` : `${A} over-called`} · ${B} with ${S}`, label: `${d.label}; ${B} with ${S}`, bR: sR });
      out.push({ key: `${o}.a`, outcome: o, side: "a", group: d.group, short: `${o === "miss" ? `${A} missed` : `${A} over-called`} · ${B} with ${A}`, label: `${d.label}; ${B} with ${A}`, bR: !sR });
    }
  }
  return out;
}

export const LAB_NAME: Record<Lab, string> = { 1: "responsive", 0: "not responsive", [-1]: "gray" };
export const LAB_SHORT: Record<Lab, string> = { 1: "R", 0: "NR", [-1]: "—" };
export const fmtN = (n: number) => n.toLocaleString("en-US");
export const fmtShare = (x: number) => (x < 0.001 && x > 0 ? "<0.1%" : `${(100 * x).toFixed(1)}%`);

/** Cohen's kappa between two labelers over units where both judged. */
export function kappa(xs: Lab[], ys: Lab[]): number | null {
  let a = 0, b = 0, c = 0, d = 0;
  for (let i = 0; i < xs.length; i++) { const x = xs[i], y = ys[i]; if (x < 0 || y < 0) continue; if (x && y) a++; else if (x) b++; else if (y) c++; else d++; }
  const n = a + b + c + d;
  if (!n) return null;
  const po = (a + d) / n, pe = ((a + b) * (a + c) + (c + d) * (b + d)) / (n * n);
  return pe === 1 ? null : (po - pe) / (1 - pe);
}
