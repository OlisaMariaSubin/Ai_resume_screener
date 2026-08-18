function category(score) {
  if (score >= 80) return { label: "Strong Match", cls: "match-strong" };
  if (score >= 60) return { label: "Moderate Match", cls: "match-moderate" };
  return { label: "Weak Match", cls: "match-weak" };
}

export default function MatchScore({ score, size = "normal" }) {
  const { label, cls } = category(score);
  return (
    <span className={`match-badge ${cls}`} style={size === "large" ? { fontSize: "1.05rem", padding: "6px 14px" } : undefined}>
      {score.toFixed(1)}% · {label}
    </span>
  );
}
