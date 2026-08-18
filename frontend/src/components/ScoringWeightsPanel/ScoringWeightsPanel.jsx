const DEFAULTS = { skill_match: 50, text_similarity: 30, experience: 10, education: 10 };

const FIELDS = [
  { key: "skill_match", label: "Skill match", help: "How much of the JD's required/nice-to-have skills the resume covers." },
  { key: "text_similarity", label: "Text similarity", help: "Overall lexical/semantic similarity between resume and JD text." },
  { key: "experience", label: "Experience", help: "How well the resume's stated experience meets the JD's requirement." },
  { key: "education", label: "Education", help: "How well the resume's degree meets the JD's requirement." },
];

export default function ScoringWeightsPanel({ weights, onChange }) {
  const active = weights || DEFAULTS;
  const total = FIELDS.reduce((sum, f) => sum + Number(active[f.key] || 0), 0);
  const ok = total === 100;

  function update(key, value) {
    onChange({ ...active, [key]: Number(value) });
  }

  return (
    <details className="advanced-panel">
      <summary>Advanced: adjust scoring weights</summary>
      <div style={{ paddingTop: 12 }}>
        <p className="muted">
          Customize how the four score components are weighted for this job. Must total 100.
        </p>
        <div className="weights-editor">
          {FIELDS.map((f) => (
            <div className="field" key={f.key}>
              <label htmlFor={`weight-${f.key}`}>{f.label}</label>
              <input
                id={`weight-${f.key}`}
                type="number"
                min="0"
                max="100"
                value={active[f.key]}
                onChange={(e) => update(f.key, e.target.value)}
              />
              <div className="muted" style={{ fontSize: "0.78rem" }}>{f.help}</div>
            </div>
          ))}
        </div>
        <div className={`weights-total ${ok ? "ok" : "bad"}`}>
          Total: {total} / 100 {ok ? "" : "— must equal 100"}
        </div>
        <button type="button" className="btn btn-ghost" style={{ marginTop: 10 }} onClick={() => onChange(null)}>
          Reset to default
        </button>
      </div>
    </details>
  );
}

export { DEFAULTS as DEFAULT_WEIGHTS };
