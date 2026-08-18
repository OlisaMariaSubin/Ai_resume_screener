import { useState } from "react";
import { api } from "../../services/api.js";

export default function ExplanationPanel({ jobId, resumeId }) {
  const [state, setState] = useState({ status: "idle", text: "" });

  async function handleExplain() {
    setState({ status: "loading", text: "" });
    try {
      const result = await api.explainScore(jobId, resumeId);
      setState({ status: "done", text: result.explanation });
    } catch (err) {
      setState({ status: "unavailable", text: err.message || "Explanations unavailable" });
    }
  }

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <h2>Explain this score</h2>
      {state.status === "idle" && (
        <button type="button" className="btn btn-secondary" onClick={handleExplain}>
          Explain this score
        </button>
      )}
      {state.status === "loading" && <p className="muted">Generating explanation…</p>}
      {state.status === "done" && (
        <>
          <p>{state.text}</p>
          <p className="disclaimer">AI-generated explanation — advisory only.</p>
        </>
      )}
      {state.status === "unavailable" && <p className="muted">Explanations unavailable.</p>}
    </div>
  );
}
