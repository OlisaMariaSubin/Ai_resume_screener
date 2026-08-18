import { useMemo, useState } from "react";
import MatchScore from "../MatchScore/MatchScore.jsx";

export default function ResultsTable({ results, onSelect }) {
  const [sortDesc, setSortDesc] = useState(true);
  const [minScore, setMinScore] = useState(0);
  const [search, setSearch] = useState("");
  const [onlyMissingMustHave, setOnlyMissingMustHave] = useState(false);

  const rows = useMemo(() => {
    let filtered = results.filter((r) => r.status === "scored");

    if (minScore > 0) filtered = filtered.filter((r) => r.score.overall >= minScore);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      filtered = filtered.filter((r) => (r.candidate_name || r.filename).toLowerCase().includes(q));
    }
    if (onlyMissingMustHave) {
      filtered = filtered.filter((r) => r.skills.missing_must_have.length > 0);
    }

    filtered = [...filtered].sort((a, b) =>
      sortDesc ? b.score.overall - a.score.overall : a.score.overall - b.score.overall,
    );

    return filtered;
  }, [results, sortDesc, minScore, search, onlyMissingMustHave]);

  const failed = results.filter((r) => r.status === "failed");

  return (
    <div>
      <div className="filters-row">
        <input
          type="text"
          placeholder="Search by candidate name"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: 220 }}
        />
        <label style={{ margin: 0, display: "flex", alignItems: "center", gap: 6 }}>
          Min score
          <input
            type="number"
            min="0"
            max="100"
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value) || 0)}
            style={{ width: 70 }}
          />
        </label>
        <label style={{ margin: 0, display: "flex", alignItems: "center", gap: 6 }}>
          <input
            type="checkbox"
            checked={onlyMissingMustHave}
            onChange={(e) => setOnlyMissingMustHave(e.target.checked)}
          />
          Missing a must-have skill
        </label>
      </div>

      <table className="results-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Candidate</th>
            <th onClick={() => setSortDesc((v) => !v)}>Match {sortDesc ? "↓" : "↑"}</th>
            <th>Matched skills</th>
            <th>Missing skills</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.candidate_id} className="clickable" onClick={() => onSelect(row)}>
              <td>{row.ranking}</td>
              <td>{row.candidate_name || row.filename}</td>
              <td>
                <MatchScore score={row.score.overall} />
              </td>
              <td>{row.skills.matched.slice(0, 4).join(", ") || "—"}</td>
              <td>{row.skills.missing.slice(0, 4).join(", ") || "—"}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={5} className="muted" style={{ textAlign: "center", padding: 24 }}>
                No candidates match the current filters.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {failed.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <h2 style={{ fontSize: "1rem" }}>Could not be screened</h2>
          <ul>
            {failed.map((f) => (
              <li key={f.candidate_id} className="muted">
                {f.filename}: {f.failure_reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
