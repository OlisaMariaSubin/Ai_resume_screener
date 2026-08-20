import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import CandidateCard from "../components/CandidateCard/CandidateCard.jsx";
import EligibilitySummaryPanel from "../components/EligibilitySummaryPanel/EligibilitySummaryPanel.jsx";
import FairnessAuditPanel from "../components/FairnessAuditPanel/FairnessAuditPanel.jsx";
import RequirementTrendsPanel from "../components/RequirementTrendsPanel/RequirementTrendsPanel.jsx";
import ResultsTable from "../components/ResultsTable/ResultsTable.jsx";
import SkillFilter from "../components/SkillFilter/SkillFilter.jsx";
import { api } from "../services/api.js";

export default function Results() {
  const { jobId } = useParams();
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [skillFilter, setSkillFilter] = useState([]);
  const [showAudit, setShowAudit] = useState(false);
  const [showTrends, setShowTrends] = useState(false);
  const [eligibilitySummary, setEligibilitySummary] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState("");

  useEffect(() => {
    api
      .getResults(jobId, skillFilter)
      .then((data) => setResults(data.results))
      .catch((err) => setError(err.message));
  }, [jobId, skillFilter]);

  useEffect(() => {
    api
      .getTrends(jobId)
      .then((data) => setEligibilitySummary(data.eligibility_summary))
      .catch(() => {});
  }, [jobId, results]);

  const handleDownloadExcel = async () => {
    setDownloading(true);
    setDownloadError("");
    try {
      await api.downloadExcel(jobId);
    } catch (err) {
      setDownloadError(err.message);
    } finally {
      setDownloading(false);
    }
  };

  const scored = useMemo(() => (results || []).filter((r) => r.status === "scored"), [results]);

  const availableSkills = useMemo(() => {
    const set = new Set();
    scored.forEach((r) => {
      r.skills.matched.forEach((s) => set.add(s));
      r.skills.missing.forEach((s) => set.add(s));
    });
    return Array.from(set).sort();
  }, [scored]);

  const stats = useMemo(() => {
    if (scored.length === 0) return null;
    const avg = scored.reduce((sum, r) => sum + r.score.overall, 0) / scored.length;
    const top = scored[0];
    return { total: scored.length, average: avg, top };
  }, [scored]);

  const weightsUsed = scored[0]?.score.weights_used;

  if (error) return <div className="error-banner">{error}</div>;
  if (!results) return <p className="muted">Loading results…</p>;

  return (
    <div className="page-enter results-page">
      <div className="page-heading results-heading">
        <div>
          <p className="eyebrow">Shortlist / 03</p>
          <h1>Screening results</h1>
          <p className="subtitle">A ranked view of fit, with the reasoning close at hand.</p>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <button type="button" className="btn btn-secondary" onClick={handleDownloadExcel} disabled={downloading}>
            {downloading ? "Preparing…" : "Download Screening Excel"}
          </button>
          <Link to={`/results/${jobId}/edit`} className="btn btn-secondary">
            Edit brief <span aria-hidden="true">-&gt;</span>
          </Link>
        </div>
      </div>

      {downloadError && <div className="error-banner">{downloadError}</div>}

      <EligibilitySummaryPanel summary={eligibilitySummary} />

      {weightsUsed && (
        <p className="weights-label">
          Scored: {weightsUsed.skill_match}% skills · {weightsUsed.text_similarity}% similarity ·{" "}
          {weightsUsed.experience}% experience · {weightsUsed.education}% education
        </p>
      )}

      {stats && (
        <div className="summary-row">
          <div className="stat-tile">
            <div className="stat-label">Total candidates</div>
            <div className="stat-value">{stats.total}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-label">Average match</div>
            <div className="stat-value">{stats.average.toFixed(1)}%</div>
          </div>
          <div className="stat-tile">
            <div className="stat-label">Top match</div>
            <div className="stat-value">{stats.top.score.overall.toFixed(1)}%</div>
          </div>
        </div>
      )}

      {availableSkills.length > 0 && (
        <div className="card">
          <SkillFilter availableSkills={availableSkills} selected={skillFilter} onChange={setSkillFilter} />
        </div>
      )}

      <div className="card">
        <ResultsTable results={results} onSelect={setSelected} />
      </div>

      <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
        <button type="button" className="btn btn-secondary" onClick={() => setShowAudit((v) => !v)}>
          {showAudit ? "Hide" : "View"} Fairness &amp; Score Audit
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => setShowTrends((v) => !v)}>
          {showTrends ? "Hide" : "View"} Requirement Trends
        </button>
      </div>

      {showAudit && <FairnessAuditPanel jobId={jobId} onClose={() => setShowAudit(false)} />}
      {showTrends && <RequirementTrendsPanel jobId={jobId} onClose={() => setShowTrends(false)} />}

      {selected && <CandidateCard jobId={jobId} candidate={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
