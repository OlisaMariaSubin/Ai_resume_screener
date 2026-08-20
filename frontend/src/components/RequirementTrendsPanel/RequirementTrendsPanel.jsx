import { useEffect, useState } from "react";
import { api } from "../../services/api.js";

const RARITY_CLASS = {
  "Very Common": "match-strong",
  Common: "match-strong",
  Moderate: "match-moderate",
  Rare: "match-weak",
  "Very Rare": "match-weak",
};

export default function RequirementTrendsPanel({ jobId, onClose }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getTrends(jobId)
      .then((res) => setData(res))
      .catch((err) => setError(err.message));
  }, [jobId]);

  const trends = data?.trends;
  const insights = data?.insights;

  return (
    <div className="card">
      <button type="button" className="btn btn-ghost" style={{ float: "right" }} onClick={onClose}>
        Dismiss
      </button>
      <h2>Requirement trends</h2>
      <p className="muted">
        How common each JD skill is across the eligible, screened applicant pool - and where the pool
        might make a requirement worth reconsidering.
      </p>

      {error && <p className="error-banner">{error}</p>}
      {!data && !error && <p className="muted">Loading trends…</p>}

      {trends &&
        (trends.length === 0 ? (
          <p className="muted">No candidates screened yet.</p>
        ) : (
          <>
            {trends.map((t) => (
              <div className="bar-row" key={t.skill}>
                <span className="bar-label">{t.skill}</span>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${t.pct_of_pool}%` }} />
                </div>
                <span className="bar-value">{t.pct_of_pool}%</span>
                <span className={`match-badge ${RARITY_CLASS[t.rarity_category] || "match-moderate"}`}>
                  {t.rarity_category}
                </span>
                {t.is_jd_must_have && <span className="muted">must-have</span>}
              </div>
            ))}

            {insights && insights.jd_requirement_gaps.length > 0 && (
              <div style={{ marginTop: 20 }}>
                <h2 style={{ fontSize: "1rem" }}>JD requirement gaps</h2>
                {insights.jd_requirement_gaps.map((gap) => (
                  <div className="flag-item" key={gap.skill}>
                    {gap.insight}
                  </div>
                ))}
              </div>
            )}

            {insights && (
              <div style={{ marginTop: 20, display: "flex", gap: 24, flexWrap: "wrap" }}>
                <div>
                  <h2 style={{ fontSize: "1rem" }}>Oversupplied skills</h2>
                  <p className="muted">
                    {insights.oversupplied_skills.length ? insights.oversupplied_skills.join(", ") : "None"}
                  </p>
                </div>
                <div>
                  <h2 style={{ fontSize: "1rem" }}>Rare skills</h2>
                  <p className="muted">
                    {insights.rare_skills.length
                      ? insights.rare_skills.map((r) => `${r.skill} (${r.pct_of_pool}%)`).join(", ")
                      : "None"}
                  </p>
                </div>
              </div>
            )}
          </>
        ))}
    </div>
  );
}
