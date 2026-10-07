"""The effect test: the pseudonymisation ablation (results/ablation/summary.json), rendered for the contamination write-ups.

Every builder (main report, split reports, paper, short report, explainers) calls `effect(summary)`; if the ablation has not been run
the result is None and the callers fall back to their future-tense text. Nothing here is computed from the ablation's own code — only
its summary.json is read — so this module may change without touching ablation/*.
"""
from __future__ import annotations

import json
from pathlib import Path

from .html import MODEL_META, _esc, _pct, dotplot, legend, table
from .run import RESULTS_DIR

ABLATION_DIR = RESULTS_DIR.parent / "ablation"
ABLATION_HREF = "../ablation/ablation_report.html"
SYSTEM_ORDER = ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "jev@base"]
ARM_LABEL = {"enron_j": "Enron · Complaint J (the knowledge is here)", "enron_k": "Enron · Complaint K (same mailbox, control)",
             "veridian": "Veridian (fictional: renaming cost only)", "j_minus_k": "Knowledge effect: ΔF1(J) − ΔF1(K)"}
ARM_ROLE = {"veridian": "floor", "j_minus_k": "effect"}
ARM_SHORT = {"enron_j": "Enron J", "enron_k": "Enron K", "veridian": "Veridian", "mnk": "Mallinckrodt"}


def _mkey(m: str) -> str:
    """Map the ablation's system key onto the contamination report's model key (jev@base -> jev)."""
    return m.split("@")[0]


def load_ablation(path: Path = ABLATION_DIR / "summary.json") -> dict | None:
    if not path.exists():
        return None
    try:
        a = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not a.get("arms") or not a.get("contrasts"):
        return None
    return a


def _pp(d: dict) -> tuple[float, float, float]:
    return 100 * d["delta"], 100 * d["lo"], 100 * d["hi"]


def _ci(d: dict, digits: int = 1) -> str:
    v, lo, hi = _pp(d)
    f = lambda x: f"{x:+.{digits}f}"  # noqa: E731
    return f"<b>{f(v)}</b> <small>[{f(lo)}, {f(hi)}]</small>"


def _ci_txt(d: dict) -> str:
    v, lo, hi = _pp(d)
    return f"{v:+.1f} [{lo:+.1f}, {hi:+.1f}]"


def _pt(v: float, nd: int = 1) -> str:
    """Signed percentage-point delta from a fraction, no % sign, no '-0.0'."""
    r = round(100 * v, nd)
    r = 0.0 if r == 0 else r
    return f"{r:+.{nd}f}"


def _r(x: float) -> int:
    """Round half up (121/200 -> 61%)."""
    return int(x + 0.5)


def _name(m: str) -> str:
    return MODEL_META[_mkey(m)][0]


def effect(summary: dict | None = None, a: dict | None = None) -> dict | None:
    """Figure, table and prose for the ablation result. None if the ablation has not been run."""
    a = a or load_ablation()
    if a is None:
        return None
    systems = [m for m in SYSTEM_ORDER if m in a["models"]] + [m for m in a["models"] if m not in SYSTEM_ORDER]
    llms = [m for m in systems if not m.startswith("jev")]
    jev = next((m for m in systems if m.startswith("jev")), None)
    keys = [_mkey(m) for m in systems]
    arms, con, leak = a["arms"], a["contrasts"], a.get("leak", {})

    def arm(m, k):
        return arms[k]["per_model"].get(m)

    # ---- figure: ΔF1 per arm and the J−K contrast, all systems, whiskers = 95% CI
    rows = []
    for k in ("enron_j", "enron_k", "veridian"):
        rows.append((k, {_mkey(m): _pp(arm(m, k)["delta"]["f1"]) for m in systems if arm(m, k)}))
    rows.append(("j_minus_k", {_mkey(m): _pp(con[m]["j_minus_k"]["f1"]) for m in systems if m in con}))
    fig = dotplot(rows, keys, -9, 9, [-8, -6, -4, -2, 0, 2, 4, 6, 8], lambda v: f"{v:+.0f}", "Effect · ΔF1 (renamed − named), percentage points, with 95% CI; last row = knowledge effect",
                  ref=0, width=720, label_w=300, row_h=44, labels=ARM_LABEL, roles=ARM_ROLE,
                  note="Each dot is one system's change in F1 when every person and organisation in the documents is consistently renamed; whiskers are paired bootstrap 95% intervals over "
                       "documents. The last row subtracts the control requests from the scandal requests on the same mailbox: what the case knowledge was worth, net of the cost of renaming.")
    fig = legend(keys) + fig

    # ---- table
    def flips(m, k):
        x = arm(m, k)
        return f"{100 * x['label_changed_share']:.1f}%" if x else "–"
    trows = []
    for m in systems:
        j, k_, v, mnk = arm(m, "enron_j"), arm(m, "enron_k"), arm(m, "veridian"), arm(m, "mnk")
        trows.append([f'<span class="m" style="--c:{MODEL_META[_mkey(m)][2]}">{_esc(_name(m))}</span>',
                      _ci(j["delta"]["f1"]) if j else "–", _ci(k_["delta"]["f1"]) if k_ else "–", _ci(con[m]["j_minus_k"]["f1"]) if m in con else "–",
                      _ci(v["delta"]["f1"]) if v else "–", _pt(v["delta"]["recall"]["delta"]) if v else "–",
                      f"{flips(m, 'enron_j')} / {flips(m, 'enron_k')}",
                      (f"{_ci(mnk['delta']['f1'])} <small>(recall {_pt(mnk['delta']['recall']['delta'])})</small>") if mnk else "–"])
    tbl = table(["system", "ΔF1 Enron J", "ΔF1 Enron K", "knowledge effect J − K", "ΔF1 Veridian", "ΔRecall Veridian", "labels flipped J / K", "Mallinckrodt: ΔF1 with the case brief"],
                trows, cls="tbl wide")

    # ---- numbers for the prose
    jk = {m: con[m]["j_minus_k"]["f1"] for m in systems if m in con}
    jk_txt = "; ".join(f"{_name(m)} {_ci_txt(jk[m])}" for m in systems if m in jk)
    jk_llm_vals = [100 * jk[m]["delta"] for m in llms if m in jk]
    any_excl = [m for m in systems if m in jk and (jk[m]["lo"] > 0 or jk[m]["hi"] < 0)]
    excl_txt = "no system’s interval excludes zero" if not any_excl else "the interval excludes zero only for " + ", ".join(_name(m) for m in any_excl)
    sign_txt = ("and the sign is not even consistent across the three LLMs" if jk_llm_vals and (min(jk_llm_vals) < 0 < max(jk_llm_vals)) else "")
    seq = lambda k, key="f1": " / ".join(_pt(arm(m, k)["delta"][key]["delta"]) for m in systems if arm(m, k))  # noqa: E731
    flip_vals = [100 * arm(m, k)["label_changed_share"] for m in systems for k in ("enron_j", "enron_k") if arm(m, k)]
    flip_txt = f"{min(flip_vals):.0f}–{max(flip_vals):.0f}%"
    ver_rec = [100 * arm(m, "veridian")["delta"]["recall"]["delta"] for m in systems if arm(m, "veridian")]
    ver_rec_txt = f"between {max(ver_rec):+.1f} and {min(ver_rec):+.1f}"
    mn_p = [arm(m, k)["mcnemar"]["p"] for m in systems for k in ("enron_j", "enron_k") if arm(m, k)]
    sys_txt = " / ".join(_name(m) for m in systems)

    # leakage (LLMs only)
    leak_models = [m for m in llms if m in leak]
    leak_share = " / ".join(f"{_r(100 * leak[m]['named_enron'] / leak[m]['n'])}%" for m in leak_models)
    leak_n = leak[leak_models[0]]["n"] if leak_models else 0
    d0 = " / ".join(f"{_r(100 * leak[m]['by_dose']['0']['named_enron'] / leak[m]['by_dose']['0']['n'])}%" for m in leak_models if "0" in leak[m].get("by_dose", {}))
    d0_n = leak[leak_models[0]]["by_dose"]["0"]["n"] if leak_models and "0" in leak[leak_models[0]].get("by_dose", {}) else 0
    leak_names = " / ".join(_name(m) for m in leak_models)

    # Jev on FAS 140
    jev_fas = None
    if jev and arm(jev, "enron_j") and "fas140" in arm(jev, "enron_j")["topics"]:
        t = arm(jev, "enron_j")["topics"]["fas140"]
        others = {m: arm(m, "enron_j")["topics"]["fas140"]["delta"]["f1"] for m in llms if arm(m, "enron_j") and "fas140" in arm(m, "enron_j")["topics"]}
        jev_fas = {"delta": t["delta"]["f1"], "lost": t["flips"]["positives_lost"], "gained": t["flips"]["positives_gained"], "n": t["named"]["n"],
                   "others": others, "pooled": arm(jev, "enron_j")["delta"]["f1"], "jk": jk.get(jev)}

    # Mallinckrodt brief
    mnk_txt = " / ".join(_pt(arm(m, "mnk")["delta"]["f1"]["delta"]) for m in systems if arm(m, "mnk"))
    mnk_jev = arm(jev, "mnk") if jev else None

    cost = a.get("total_paid_usd")

    # the classifier-native follow-up (bare-token check and code-name swap), if it has been run; it closes the FAS 140 question below
    from .jevnative import jev_native  # noqa: PLC0415  (jevnative imports this module; import lazily)

    nat = jev_native()
    bare = nat["bare"] if nat and nat["bare"]["aswritten"] else None
    followup = ((f" The token check this request called for has since been run (classifier-native tests): a header plus one sentence naming a vehicle is called responsive "
                 f"{_pct(bare['aswritten']['rate_real'])} of the time under the request as written (fictional twin {_pct(bare['aswritten']['rate_fake'])}) and "
                 f"{_pct(bare['named']['rate_real'])} vs {_pct(bare['named']['rate_fake'])} only when the criteria name the vehicles, so the loss is not a bare-name reflex; "
                 f"the code-name swap then found the same case knowledge on four matters at effect sizes comparable to the LLMs’ ({nat['t1_jev_short']} pp). "
                 f"{nat['overall']}") if bare else "")

    # round 2 (CUAD paraphrase, Jeb Bush) extends the bound to other matters; only its presence is checked here (effect2 imports this module)
    from .effect2 import load_round2  # noqa: PLC0415

    has_r2 = load_round2() is not None
    bound_txt = ("That is a bound on one matter at this sample size, not a demonstration of no effect: smaller effects, other matters and knowledge that survives renaming are not excluded."
                 if not has_r2 else
                 "On its own that is a bound on one matter at this sample size; round 2 (below) carries the same test to Jeb Bush and, with paraphrase in place of renaming, to CUAD, "
                 "and the generalisation checks ask where in the corpus the knowledge could have helped. Smaller effects and knowledge that survives every manipulation are not excluded.")

    # ---- prose
    result = (f"<p>Renaming every person and organisation in the documents and classifying them again changed F1 by {seq('enron_j')} points ({sys_txt}) on the "
              f"Enron Complaint J requests, where Part II found the case knowledge; by {seq('enron_k')} on the Complaint K control requests on the same mailbox; and by "
              f"{seq('veridian')} on the fictional Veridian, where the names carry no knowledge and renaming can only cost. The <b>knowledge effect</b> — ΔF1(J) − ΔF1(K) — is "
              f"{jk_txt}: {excl_txt}{', ' + sign_txt if sign_txt else ''}. Renaming flipped {flip_txt} of individual labels (McNemar p ≥ {min(mn_p):.2f} on both Enron arms) and cost "
              f"{ver_rec_txt} points of recall on Veridian. The measured effect of name-mediated case knowledge on a full-document relevance call is therefore within the noise of the "
              f"renaming operation itself — on the one corpus where every exposure probe said the knowledge was largest and most specific. {bound_txt}</p>")
    leak_p = (f"<p><b>The test is not clean, and that bounds what it can say.</b> Asked afterwards which company the <em>renamed</em> Enron documents came from — production headers "
              f"stripped, ticker mapped — the models still named Enron in {leak_share} of a {leak_n}-document sample ({leak_names}), and in {d0} of the {d0_n} documents that contained no "
              f"knowledge-bearing name at all. They recognise the case from the fact pattern (the deals, the dates, the business), not from the names. The ablation therefore removes "
              f"only the name channel: Δ is a <em>lower bound</em> on the effect of case knowledge, and the evidence is that the names are not the main channel through which it would act. "
              f"A clean effect test on Enron would need the fact pattern rewritten, which for a real matter is impossible without destroying the documents; the way forward is a "
              f"corpus the models have not seen.</p>") if leak_models else ""
    jev_p = ""
    if jev_fas:
        o = jev_fas["others"]
        o_txt = ", ".join(f"{_name(m)} {_pt(o[m]['delta'])}" for m in llms if m in o)
        jev_p = (f"<p><b>Jev on FAS 140.</b> One request moves against the grain. On the FAS 140 request (special-purpose-entity accounting) Jev’s F1 fell "
                 f"{_pt(jev_fas['delta']['delta'])} points [{_pt(jev_fas['delta']['lo'])}, {_pt(jev_fas['delta']['hi'])}] on renaming — {jev_fas['lost']} positives lost, "
                 f"{jev_fas['gained']} gained, of {jev_fas['n']} documents — while the LLMs on the same request moved {o_txt}. "
                 + ("Seven of Jev’s twelve lost positives are documents that name the Raptor, Talon, LJM2 and Chewco vehicles (its probability of responsiveness fell from 0.5–0.6 to "
                    "0.1–0.4 on them); the other five were marginal calls near 0.5. " if jev_fas['lost'] == 12 and jev_fas['gained'] == 0 else "")
                 + f"Read one way, this is the one piece of evidence in the study that Jev’s output depends on specific Enron tokens, which is what a system that had seen the Enron record "
                 f"would show; read the other way, those tokens are strong lexical cues for this request that any classifier could weight and lose when they are replaced. Pooled over "
                 f"Complaint J Jev’s knowledge effect is {_ci_txt(jev_fas['jk'])}, indistinguishable from the LLMs’. The vendor’s statement that Jev is not pre-trained on these corpora "
                 f"remains a claim under test"
                 + (f"; this request is where the next check belongs (a token check: does Jev’s probability move on ‘Raptor’ alone, outside any document?).</p>" if not followup
                    else f".{followup}</p>"))
    brief_p = (f"<p><b>Mallinckrodt, with and without the case brief.</b> Giving each system a short brief on the matter in place of the bare request changed F1 by {mnk_txt} "
               f"({sys_txt})" + (f"; Jev’s gain is recall ({_pt(mnk_jev['delta']['recall']['delta'])} points) at a small cost in precision" if mnk_jev else "") +
               ". Supplying the case knowledge explicitly moves the LLMs by less than a point — the same order as the knowledge effect measured by removal.</p>")

    one_sentence = (f"The pseudonymisation ablation has been run: renaming every person and organisation changes F1 by {seq('enron_j')} points on the Enron scandal requests "
                    f"({sys_txt}), with a knowledge effect (J − K) of {jk_txt}; {excl_txt}.")
    one_sentence_jev = (f"On the full-document ablation Jev’s knowledge effect is {_ci_txt(jk[jev])} points, indistinguishable from the LLMs’ ({', '.join(_pt(jk[m]['delta']) for m in llms if m in jk)}); "
                        f"one request (FAS 140, {_pt(jev_fas['delta']['delta'])} points on renaming) is the one place in the ablation where Jev’s output moved with Enron-specific tokens, "
                        f"and it is reported as under-test evidence, not as a verdict.") if jev and jev in jk and jev_fas else ""

    # plain-English (lawyer / explainer)
    plain = (f"<p>Think of it as changing the names on every exhibit and running the review again. We took the Enron e-mails, consistently replaced every person and company with "
             f"an invented one — the same fake name every time a real one appeared — and asked each system to make the same relevance calls on the renamed set. If a system had "
             f"been leaning on what it already knew about Enron’s people and deals, its score should fall when the names it recognises are taken away. For comparison we did the "
             f"same on the unrelated oil-spill requests from the same mailbox (where there is little to know) and on the fictional Veridian collection (where renaming can only cost).</p>"
             f"<p>The scores barely moved. On the Enron scandal requests the change in F1 was {seq('enron_j')} points ({sys_txt}); on the control requests {seq('enron_k')}; on Veridian "
             f"{seq('veridian')}. The difference that measures the knowledge — scandal requests minus control requests — was {jk_txt}, and {excl_txt}. Renaming changed about "
             f"{flip_txt} of individual calls either way, which is the noise the operation itself introduces.</p>"
             + (f"<p><b>One caveat in plain words.</b> When we afterwards asked the models which company the renamed documents came from, they still said Enron for {leak_share} of them "
                f"({leak_names}) — they recognised the case from the story itself, not from the names. So renaming is not a clean test of what the knowledge is worth: the small effect "
                f"we measured is a floor, not a ceiling. It does show that the names are not how the knowledge would help.</p>" if leak_models else "")
             + (f"<p><b>Jev.</b> The classifier under evaluation went through the same test. Its vendor says it was not trained on public text; we treat that as a claim. Overall its "
                f"result was the same as the language models’ ({_ci_txt(jk[jev])} points), which is consistent with the claim. On one request its score did fall when the names were changed "
                f"({_pt(jev_fas['delta']['delta'])} points on FAS 140, and the documents it lost are largely the ones naming Enron’s off-books vehicles). That is the one place in the renaming test where the "
                f"evidence points the other way"
                + (", and it is recorded as a question to follow up, not as an answer.</p>" if not bare else
                   f". We followed it up with tests built for a classifier: a bare vehicle name on its own does not trigger the request ({_pct(bare['aswritten']['rate_real'])} responsive as "
                   f"written, {_pct(bare['named']['rate_real'])} once the request names the vehicles), and a code-name swap on four matters shows Jev, like the language models, recognises "
                   f"the real names of the cases. In plain terms: the tests are consistent with Jev not having been trained on these collections, and they show it knows the cases behind "
                   f"them about as well as the language models do; knowing the case did not measurably change its Enron score.</p>") if jev and jev in jk and jev_fas else ""))
    plain_howto = ("Each row is a set of requests; each dot is one system. The dot’s position is how much the F1 score changed when every name was replaced: left of the dashed line "
                   "means renaming hurt, right means it helped. The thin line through each dot is the range of values consistent with the data (95%). The bottom row is the one that "
                   "matters: scandal requests minus control requests, i.e. the effect of knowing the case. A dot whose line crosses zero is a result that could be chance.")

    return {"has": True, "fig": fig, "tbl": tbl, "result": result, "leak": leak_p, "jev": jev_p, "brief": brief_p, "one_sentence": one_sentence,
            "one_sentence_jev": one_sentence_jev, "plain": plain, "plain_howto": plain_howto, "cost": cost, "href": ABLATION_HREF, "jk": jk, "systems": systems,
            "leak_share": leak_share, "leak_names": leak_names, "jk_txt": jk_txt, "excl_txt": excl_txt, "flip_txt": flip_txt, "ver_rec_txt": ver_rec_txt,
            "jev_fas": jev_fas, "seq_j": seq("enron_j"), "seq_k": seq("enron_k"), "seq_v": seq("veridian"), "sys_txt": sys_txt}
