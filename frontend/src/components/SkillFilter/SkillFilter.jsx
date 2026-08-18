import { useState } from "react";

export default function SkillFilter({ availableSkills, selected, onChange }) {
  const [customSkill, setCustomSkill] = useState("");

  function toggle(skill) {
    if (selected.includes(skill)) {
      onChange(selected.filter((s) => s !== skill));
    } else {
      onChange([...selected, skill]);
    }
  }

  function addCustom() {
    const trimmed = customSkill.trim();
    if (trimmed && !selected.includes(trimmed)) {
      onChange([...selected, trimmed]);
    }
    setCustomSkill("");
  }

  return (
    <div>
      <label htmlFor="skill-filter-select">Filter by required skill(s)</label>
      <select
        id="skill-filter-select"
        multiple
        size={Math.min(6, Math.max(3, availableSkills.length))}
        value={selected}
        onChange={(e) => onChange(Array.from(e.target.selectedOptions, (o) => o.value))}
        style={{ marginBottom: 8 }}
      >
        {availableSkills.map((skill) => (
          <option key={skill} value={skill}>
            {skill}
          </option>
        ))}
      </select>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          type="text"
          placeholder="Add a skill not listed"
          value={customSkill}
          onChange={(e) => setCustomSkill(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && addCustom()}
        />
        <button type="button" className="btn btn-secondary" onClick={addCustom}>
          Add
        </button>
      </div>
      {selected.length > 0 && (
        <div style={{ marginTop: 10 }}>
          {selected.map((skill) => (
            <span className="skill-chip matched" key={skill} onClick={() => toggle(skill)} style={{ cursor: "pointer" }}>
              {skill} ×
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
