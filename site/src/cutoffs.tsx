import { Component, StrictMode } from "react";
import { createRoot } from "react-dom/client";
import CutoffsPage from "./CutoffsPage";
import "./styles.css";

// Entry for cutoffs.html (the unlinked per-issue cutoff explorer). Lower-case and distinct from CutoffsPage.tsx: on a case-insensitive
// filesystem `cutoffs.tsx` and `Cutoffs.tsx` would be one file.

/** Without a boundary a throw during render or in an effect unmounts the root and leaves a blank page; this keeps a way back. */
class Boundary extends Component<Record<string, never>, { error: Error | null; gen: number }> {
  state = { error: null as Error | null, gen: 0 };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(error: Error) { console.error("cutoffs page failed to render", error); }
  reset = () => {
    try { history.replaceState(null, "", location.pathname + location.search); } catch { /* ignore */ }
    try { localStorage.removeItem("theme"); } catch { /* ignore */ }
    this.setState((s) => ({ error: null, gen: s.gen + 1 }));
  };
  render() {
    if (this.state.error) {
      return (
        <div className="page cutoffs">
          <div className="card cut-fault">
            <b className="card-t">Something went wrong rendering this view</b>
            <p className="cut-note">{this.state.error.message}</p>
            <button type="button" className="studio-btn" onClick={this.reset}>Reset cutoffs</button>
          </div>
        </div>
      );
    }
    return <CutoffsPage key={this.state.gen} />;
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Boundary />
  </StrictMode>,
);
