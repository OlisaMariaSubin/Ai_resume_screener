import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import JobDescriptionInput from "../components/JobDescriptionInput/JobDescriptionInput.jsx";
import LoadingState from "../components/LoadingState/LoadingState.jsx";
import { api } from "../services/api.js";

const STAGES = [
  "Updating job description…",
  "Re-comparing resumes…",
  "Recalculating match scores…",
];

export default function RerunScreening() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState({ title: "", description: "", scoringWeights: null });
  const [resumes, setResumes] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [stageIndex, setStageIndex] = useState(0);
  const intervalRef = useRef(null);

  useEffect(() => () => clearInterval(intervalRef.current), []);

  useEffect(() => {
    Promise.all([api.getJob(jobId), api.getResults(jobId)])
      .then(([jobData, resultsData]) => {
        setJob({
          title: jobData.title,
          description: jobData.description,
          scoringWeights: jobData.scoring_weights,
        });
        setResumes(resultsData.results.filter((r) => r.filename));
      })
      .catch((err) => setError(err.message));
  }, [jobId]);

  const canSubmit = job.description.trim().length > 0 && resumes.length > 0 && !loading;

  async function handleRerun() {
    setError("");
    setLoading(true);
    setStageIndex(0);
    intervalRef.current = setInterval(() => {
      setStageIndex((i) => Math.min(i + 1, STAGES.length - 1));
    }, 900);

    try {
      await api.updateJob(jobId, {
        title: job.title,
        description: job.description,
        scoringWeights: job.scoringWeights,
      });
      await api.rerunScreening(jobId);
      navigate(`/results/${jobId}`);
    } catch (err) {
      setError(err.message || "Something went wrong while re-running screening.");
      setLoading(false);
      clearInterval(intervalRef.current);
    }
  }

  if (loading) {
    return <LoadingState stage={STAGES[stageIndex]} />;
  }

  if (error && !job.description) {
    return <div className="error-banner">{error}</div>;
  }

  return (
    <div>
      <h1>Edit job description</h1>
      <p className="subtitle">
        Update the job description and re-run screening against the same uploaded resumes.
      </p>

      {error && <div className="error-banner">{error}</div>}

      <JobDescriptionInput value={job} onChange={setJob} />

      <div className="card">
        <h2>Resumes to re-screen</h2>
        {resumes.length === 0 ? (
          <p className="muted">No stored resumes found for this screening.</p>
        ) : (
          <ul className="file-list">
            {resumes.map((resume) => (
              <li className="file-row" key={resume.candidate_id}>
                <span>
                  {resume.filename || resume.candidate_name || "Resume"}
                  {resume.candidate_name ? (
                    <span className="muted"> — {resume.candidate_name}</span>
                  ) : null}
                </span>
                <span className="file-status pending">saved</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <button type="button" className="btn btn-primary" disabled={!canSubmit} onClick={handleRerun}>
          Re-run screening
        </button>
        <Link to={`/results/${jobId}`} className="btn btn-secondary">
          Cancel
        </Link>
      </div>
    </div>
  );
}
