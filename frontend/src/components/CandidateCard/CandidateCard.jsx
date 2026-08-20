import { useState } from "react";
import MatchScore from "../MatchScore/MatchScore.jsx";
import SkillList from "../SkillList/SkillList.jsx";
import ExplanationPanel from "../ExplanationPanel/ExplanationPanel.jsx";
import { api } from "../../services/api.js";

export default function CandidateCard({ jobId, candidate, onClose }) {
  const { score, skills } = candidate;
  const [resumeState, setResumeState] = useState({ status: "idle", text: "" });

  async function handleViewResume() {
    setResumeState({ status: "loading", text: "" });
    try {
      const result = await api.getResumeContent(candidate.candidate_id);
      setResumeState({ status: "done", text: result.raw_text });
    } catch (err) {
      setResumeState({ status: "error", text: err.message || "Could not load the resume." });
    }
  }

  return (
    <div className="candidate-modal-backdrop" onClick={onClose}>
      <div className="candidate-modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
          ×
        </button>
        <h2>{candidate.candidate_name || candidate.filename}</h2>
        {candidate.status === "failed" ? (
          <p className="muted">Could not be parsed: {candidate.failure_reason}</p>
        ) : (
          <>
            <div className="candidate-actions">
              <button type="button" className="btn btn-secondary" onClick={handleViewResume} disabled={resumeState.status === "loading"}>
                {resumeState.status === "loading" ? "Loading resume..." : "View resume"}
              </button>
              <span className="muted">{candidate.filename}</span>
            </div>
            {resumeState.status === "done" && (
              <div className="resume-viewer">
                <div className="resume-viewer-heading">
                  <strong>Extracted resume text</strong>
                  <span className="muted">Read-only</span>
                </div>
                <pre>{resumeState.text || "No text was extracted from this resume."}</pre>
              </div>
            )}
            {resumeState.status === "error" && <p className="error-text">{resumeState.text}</p>}
            <div style={{ margin: "12px 0" }}>
              <MatchScore score={score.overall} size="large" />
            </div>

            <h2 style={{ fontSize: "1rem" }}>Score breakdown</h2>
            <ul>
              <li>Skill match: {score.skill_match_pct}%</li>
              <li>TF-IDF text similarity: {(score.tfidf_similarity * 100).toFixed(1)}%</li>
              {score.embedding_similarity != null && (
                <li>Embedding similarity: {(score.embedding_similarity * 100).toFixed(1)}%</li>
              )}
            </ul>
            <p className="weights-label">
              Weights used: {score.weights_used.skill_match}% skills · {score.weights_used.text_similarity}% similarity ·{" "}
              {score.weights_used.experience}% experience · {score.weights_used.education}% education
            </p>

            <h2 style={{ fontSize: "1rem" }}>Skills</h2>
            <SkillList
              matched={skills.matched}
              missingMustHave={skills.missing_must_have}
              missingNiceToHave={skills.missing_nice_to_have}
            />

            <p className="disclaimer">
              This score reflects skill and text overlap with the job description — not a hiring probability.
            </p>

            <ExplanationPanel jobId={jobId} resumeId={candidate.candidate_id} />
          </>
        )}
      </div>
    </div>
  );
}
