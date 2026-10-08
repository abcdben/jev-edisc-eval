import { useEffect, useState } from "react";
import { CORPORA, DATA, PRIMARY, corpusKey, fmtInt } from "./data";
import { Seg } from "./components/ui";
import { DisclaimerLink, DisclaimerModal } from "./components/Disclaimer";
import { THEME_KEY, THEME_OPTIONS, readTheme, type Theme } from "./theme";

/**
 * The landing page (index.html → landing.tsx): the site's title, two sentences on what it is, and a card per page. The comparison app lives at
 * compare.html with its three views in the hash (#compare, #configurations, #tradeoff; App.tsx pageOf); the study and the explorer are their own
 * pages; the contamination write-up is a static page staged under public/contamination/ by scripts/publish_writeup.sh. Links are relative so the
 * site works at the domain root and under the GitHub Pages path alike. index.html itself forwards the app's old hash links (the root used to be
 * the app) to compare.html before this renders.
 */

/** The results archive: per-decision records as one .tar.zst per corpus on the GitHub Release (results/README.md); the aggregates are tracked in the repository. */
const RELEASE_HREF = "https://github.com/abcdben/jev-edisc-eval/releases/tag/v1.0-results";
const REPO_HREF = "https://github.com/abcdben/jev-edisc-eval";

type Card = { href: string; kicker: string; title: string; what: string; can: string };
const CARDS: Card[] = [
  {
    href: "./compare.html#compare", kicker: "Jev vs Frontier LLMs", title: "Compare models",
    what: "Recall against precision for the headline roster, with 95% intervals; speed, cost per 100,000 documents and run-to-run stability beside it.",
    can: "Pick the models and TAR workflows, move the probability threshold, open any mark for the figures behind it.",
  },
  {
    href: "./compare.html#configurations", kicker: "Jev vs Frontier LLMs", title: "Compare configurations",
    what: "Every configuration of one model family (Jev, OpenAI Decisions, Laya) on the same axes, each value differenced against the family's base form.",
    can: "Choose the family; switch between the map and the ranked rows, open any configuration for its figures.",
  },
  {
    href: "./compare.html#tradeoff", kicker: "Jev vs Frontier LLMs", title: "Trade-off",
    what: "Recall against precision as a full curve per model, swept over the probability threshold, with iso-F1 contours behind.",
    can: "Drag the operating point on each curve, or match every model to a target recall and read off the cut, precision and review depth.",
  },
  {
    href: "./study.html", kicker: "Study", title: "Machine review vs. the reviewers",
    what: "Decision models, LLMs and classical TAR beside the human reviewers who built the test collections, by dataset and experiment.",
    can: "Plot one experiment or table them all; set the simulated TAR reviewer's error rates.",
  },
  {
    href: "./contamination/", kicker: "Study", title: "Does the model already know the case?",
    what: "Six collections at graded public exposure, four systems, three tests: do the models know the cases, have they memorised the documents, and does knowing change the review score. The knowledge effect is within a few F1 points.",
    can: "Read the technical write-up; browse the figure gallery.",
  },
  {
    href: "./explore.html", kicker: "Documents", title: "Population explorer",
    what: "Every judged document of a collection, cut by who called it responsive: a standard, an arm and an overlay, each a human signal or a model.",
    can: "Click a region to list its documents and read them; switch the view between mosaic, flow, Venn and confidence.",
  },
];

/** Counts for the facts line, read from findings.json so they follow the data: the corpora the comparison offers and their documents and issues, the roster size. */
function facts(): string {
  const metas = CORPORA.map((c) => DATA.corpora[corpusKey(c.id, "")]).filter(Boolean);
  const docs = metas.reduce((a, m) => a + m.n_docs, 0);
  const issues = metas.reduce((a, m) => a + m.n_issues, 0);
  const models = PRIMARY.filter((p) => !p.key.startsWith("tar@")).length;
  return `${metas.length} corpora · ${fmtInt(docs)} documents · ${issues} issues · ${models} models and configurations on the roster, plus classical TAR`;
}

export default function LandingPage() {
  const [theme, setTheme] = useState<Theme>(readTheme);
  useEffect(() => { document.documentElement.dataset.theme = theme; try { localStorage.setItem(THEME_KEY, theme); } catch { /* storage denied: the choice lasts the session */ } }, [theme]);
  const [about, setAbout] = useState(false);
  return (
    <div className="page landing">
      <header className="masthead">
        <h1 className="title">eDiscovery Review Benchmarks</h1>
        <span className="theme"><Seg value={theme} onChange={setTheme} options={THEME_OPTIONS} /></span>
      </header>

      <p className="landing-lede">
        Evaluations of machine relevance review for discovery on public and synthetic collections: decision models (TypeSafe Jev, OpenAI's Decisions
        API, Laya) against commercially available language models and classical TAR, on the same criteria and documents, with no training on examples
        and no prompt iteration. The pages cover the zero-shot bakeoff, a study anchored on the human reviewers who built the collections, a
        document-level explorer, and a contamination study asking whether the models already knew the cases; every figure is a point-in-time snapshot
        with its interval and its counts behind it.
      </p>
      <p className="landing-facts num">{facts()}</p>

      <div className="landing-grid">
        {CARDS.map((c) => (
          <a key={c.href} className="card landing-card" href={c.href}>
            <span className="kicker">{c.kicker}</span>
            <h3>{c.title}</h3>
            <p>{c.what}</p>
            <span className="do">{c.can}</span>
          </a>
        ))}
      </div>

      <p className="landing-also">
        Data: per-decision records for every run are on the <a href={RELEASE_HREF}>GitHub release</a> (CC BY 4.0); the aggregates behind these pages,
        the benchmark code and the criteria are in the <a href={REPO_HREF}>repository</a>.
      </p>

      {about && <DisclaimerModal onClose={() => setAbout(false)} />}
      <footer className="notes">
        <DisclaimerLink onClick={() => setAbout(true)} />
      </footer>
    </div>
  );
}
