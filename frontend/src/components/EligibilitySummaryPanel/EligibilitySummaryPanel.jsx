export default function EligibilitySummaryPanel({ summary }) {
  if (!summary) return null;

  const tiles = [
    { label: "Total uploaded", value: summary.total_uploaded },
    { label: "Eligible", value: summary.eligible },
    { label: "Ineligible", value: summary.ineligible },
    { label: "Not screened", value: summary.not_screened },
    { label: "Overqualified", value: summary.overqualified },
  ];

  return (
    <div className="card">
      <h2>Eligibility summary</h2>
      <p className="muted">
        Candidates who failed the mandatory education pre-screen are excluded from scoring - see the
        eligibility reasons in the results table below.
      </p>
      <div className="summary-row" style={{ marginBottom: 0 }}>
        {tiles.map((t) => (
          <div className="stat-tile" key={t.label}>
            <div className="stat-label">{t.label}</div>
            <div className="stat-value">{t.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
