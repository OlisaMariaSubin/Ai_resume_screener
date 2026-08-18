import { useEffect, useState } from "react";
import { api } from "../../services/api.js";

export default function FairnessAuditPanel({ jobId, onClose }) {
  const [audit, setAudit] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getAudit(jobId)
      .then(setAudit)
      .catch((err) => setError(err.message));
  }, [jobId]);

  return (
    <div className="card">
      <button type="button" className="btn btn-ghost" style={{ float: "right" }} onClick={onClose}>
        Dismiss
      </button>
      <h2>Fairness &amp; score audit</h2>
      <p className="muted">
        This is a fairness-of-process check, not a demographic inference. No protected attributes are ever guessed
        or stored.
      </p>

      {error && <p className="error-banner">{error}</p>}
      {!audit && !error && <p className="muted">Loading audit…</p>}

      {audit && (
        <>
          <h2 style={{ fontSize: "1rem" }}>JD language flags</h2>
          {audit.jd_language_flags.length === 0 ? (
            <p className="muted">No flagged language detected.</p>
          ) : (
            audit.jd_language_flags.map((flag, i) => (
              <div className="flag-item" key={i}>
                <strong>{flag.category.replaceAll("_", " ")}</strong>: "{flag.phrase}"
              </div>
            ))
          )}

          <h2 style={{ fontSize: "1rem", marginTop: 20 }}>Score distribution</h2>
          {Object.entries(audit.score_distribution.score_distribution).map(([label, count]) => (
            <div className="bar-row" key={label}>
              <span className="bar-label">{label}</span>
              <div className="bar-track">
                <div
                  className="bar-fill"
                  style={{
                    width: audit.score_distribution.total_candidates
                      ? `${(100 * count) / audit.score_distribution.total_candidates}%`
                      : "0%",
                  }}
                />
              </div>
              <span className="bar-value">{count}</span>
            </div>
          ))}

          <h2 style={{ fontSize: "1rem", marginTop: 20 }}>Exclusion by must-have skill</h2>
          {audit.score_distribution.excluded_by_must_have_skill.length === 0 ? (
            <p className="muted">No must-have skill excludes a notable share of the pool.</p>
          ) : (
            audit.score_distribution.excluded_by_must_have_skill.map((entry) => (
              <div className="bar-row" key={entry.skill}>
                <span className="bar-label">{entry.skill}</span>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${entry.pct_of_pool}%`, background: "#b7791f" }} />
                </div>
                <span className="bar-value">{entry.pct_of_pool}%</span>
              </div>
            ))
          )}
        </>
      )}
    </div>
  );
}
