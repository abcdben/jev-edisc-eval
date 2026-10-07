import { displayMeta, fmtInt, type Rec } from "./data";
import { fmtRate, gridFor, sameReviewer, type Reviewer } from "./tarGrid";

/**
 * The names of the TAR workflow rows as the Compare page builds them (the TAR workflow picker, the recall/precision items, the Cost and Speed cards;
 * the Studio draws the same items): the workflow's independent variables read off the model key and the run's own sidecar, with the reviewer's
 * coding accuracy as the published run assumed it ("Perfect coding", "90% relevant-document coding accuracy"). Under a TAR reviewer setting
 * (tarGrid.ts applyReviewer) that moves a row off its published rates, `movedName` replaces that part with the applied cell's rates and adds a ‡,
 * so a row never says "Perfect coding" while it is drawn at a 10% miss rate; at `published` every name is unchanged.
 */
export type TarOption = { row: Rec; n: number | null; sampling: "Random" | "Diversity" | null; reviewer: string; order: number };

/** The reviewer's relevant-document coding accuracy as the TAR names say it, from the run's own sidecar (tar.reviewer.miscode_rate, the miss rate); "perfect coding" at zero; null for a row without one. */
const codingText = (row: Rec, cap = false): string | null => {
  const m = row.tar?.reviewer.miscode_rate; if (m == null) return null;
  const s = m > 0 ? `${Math.round((1 - m) * 100)}% relevant-document coding accuracy` : "perfect coding";
  return cap ? s[0].toUpperCase() + s.slice(1) : s;
};
/** The reviewer part of a moved row's name: the applied cell's two rates. */
export const ratesText = (rev: Reviewer) => `misses ${fmtRate(rev.fn)} / over-codes ${fmtRate(rev.fp)}`;

/** A TAR row's independent variables; with `rev`, the reviewer part is the applied rates rather than the published run's coding accuracy. */
export function tarOption(row: Rec, rev?: Reviewer): TarOption {
  const v = row.model.replace(/^tar@/, "");
  if (v.startsWith("cal")) {
    const stop = v === "cal" || v === "cal_perfect" ? "80% recall target" : v === "cal_75" ? "75% recall target" : v === "cal_knee" ? "Knee stop" : null;
    const coding = rev ? ratesText(rev) : codingText(row) ?? (v === "cal_perfect" ? "perfect coding" : "90% relevant-document coding accuracy");
    const reviewer = stop ? `${stop} · ${coding}` : rev ? `${row.name.replace(/^TAR 2\.0\s*·?\s*/, "")} · ${coding}` : row.name.replace(/^TAR 2\.0\s*·?\s*/, "");
    return { row, n: null, sampling: null, reviewer, order: { cal: 0, cal_75: 1, cal_perfect: 2, cal_knee: 3 }[v] ?? 9 };
  }
  const m = /^t1_(\d+)(.*)$/.exec(v);
  const n = m ? Number(m[1]) : 0, suffix = m?.[2] ?? "";
  const sampling = suffix.endsWith("_div") ? "Diversity" : "Random";
  const acc = /_acc(\d+)/.exec(suffix)?.[1];
  const coding = rev ? ratesText(rev) : codingText(row, true) ?? (acc ? `${acc}% relevant-document coding accuracy` : suffix.includes("_noisy") ? "90% relevant-document coding accuracy" : "Perfect coding");
  const reviewer = acc ? `${coding}${acc === "90" ? " · sweep" : ""}` : suffix.includes("_noisy") ? `${coding} · baseline` : suffix.includes("_f1") ? `${coding} · F1 cutoff` : `${coding} · 80% recall cutoff`;
  return { row, n, sampling, reviewer, order: (sampling === "Random" ? 0 : 10) + (acc ? Number(acc) / 10 : suffix.includes("_noisy") ? 9 : suffix.includes("_f1") ? 8 : 0) };
}

export const tarName = (x: TarOption) => x.n == null
  ? `TAR 2.0 · CAL · ${x.reviewer}`
  : `TAR 1.0 · ${fmtInt(x.n)} reviewed · ${x.sampling?.toLowerCase()} · ${x.reviewer}`;
/** A Compare models row's name: the TAR name for a TAR row, the roster's short name otherwise. */
export const compareName = (r: Rec) => r.model.startsWith("tar@") ? tarName(tarOption(r)) : displayMeta(r.model, r).short;
/** A TAR row's name under the reviewer rates it was re-run at, when they are not its published ones: "TAR 1.0 · 1,000 reviewed · diversity · misses 10% / over-codes 2% · 80% recall cutoff ‡". */
export const movedName = (r: Rec, rev: Reviewer) => `${tarName(tarOption(r, rev))} ‡`;

/**
 * Whether a TAR record, as handed to a chart, sits off its published reviewer rates: applyReviewer writes the applied cell's rates into the sidecar,
 * and the grid's default is the published pair, so the two differ exactly for the ‡ rows. False for any record without a grid (fixed at published).
 */
export function offPublishedRec(r: Rec): boolean {
  const g = gridFor(r.corpus, r.model), rv = r.tar?.reviewer;
  return !!g && !!rv && !sameReviewer({ fn: rv.miscode_rate, fp: rv.fp_rate ?? rv.miscode_rate / 5 }, g.default);
}
/** A chart row's name for a TAR record under the reviewer setting (opsRows.ts; the Cost and Speed charts the grid reaches): the roster's short name, with the applied rates and a ‡ when off published. */
export const gridRowName = (r: Rec, short: string): string => {
  const rv = r.tar?.reviewer;
  return rv && offPublishedRec(r) ? `${short} · ${ratesText({ fn: rv.miscode_rate, fp: rv.fp_rate ?? rv.miscode_rate / 5 })} ‡` : short;
};
