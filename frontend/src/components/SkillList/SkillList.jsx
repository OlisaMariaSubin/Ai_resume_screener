export default function SkillList({ matched = [], missingMustHave = [], missingNiceToHave = [] }) {
  return (
    <div>
      {matched.length > 0 && (
        <div style={{ marginBottom: 6 }}>
          {matched.map((skill) => (
            <span className="skill-chip matched" key={`m-${skill}`}>
              {skill}
            </span>
          ))}
        </div>
      )}
      {missingMustHave.length > 0 && (
        <div style={{ marginBottom: 6 }}>
          {missingMustHave.map((skill) => (
            <span className="skill-chip missing" key={`mm-${skill}`}>
              {skill} (required)
            </span>
          ))}
        </div>
      )}
      {missingNiceToHave.length > 0 && (
        <div>
          {missingNiceToHave.map((skill) => (
            <span className="skill-chip missing-nice" key={`mn-${skill}`}>
              {skill} (preferred)
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
