import { useEffect, useState } from "react";
import { api } from "../../services/api.js";

export default function RequirementTrendsPanel({ jobId, onClose }) {
  const [trends, setTrends] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getTrends(jobId)
      .then((data) => setTrends(data.trends))
      .catch((err) => setError(err.message));
  }, [jobId]);

  return (
    <div className="card">
      <button type="button" className="btn btn-ghost" style={{ float: "right" }} onClick={onClose}>
        Dismiss
      </button>
      <h2>Requirement trends</h2>
      <p className="muted">
        How common each JD skill is across the screened applicant pool — a signal for which requirements are
        realistic versus effectively screening everyone out.
      </p>

      {error && <p className="error-banner">{error}</p>}
      {!trends && !error && <p className="muted">Loading trends…</p>}

      {trends &&
        (trends.length === 0 ? (
          <p className="muted">No candidates screened yet.</p>
        ) : (
          trends.map((t) => (
            <div className="bar-row" key={t.skill}>
              <span className="bar-label">{t.skill}</span>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${t.pct_of_pool}%` }} />
              </div>
              <span className="bar-value">{t.pct_of_pool}%</span>
            </div>
          ))
        ))}
    </div>
  );
}
