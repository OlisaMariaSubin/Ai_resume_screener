import MatchScore from "../MatchScore/MatchScore.jsx";
import SkillList from "../SkillList/SkillList.jsx";
import ExplanationPanel from "../ExplanationPanel/ExplanationPanel.jsx";

export default function CandidateCard({ jobId, candidate, onClose }) {
  const { score, skills } = candidate;

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
