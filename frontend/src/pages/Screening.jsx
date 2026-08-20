import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import JobDescriptionInput from "../components/JobDescriptionInput/JobDescriptionInput.jsx";
import LoadingState from "../components/LoadingState/LoadingState.jsx";
import ResumeUpload from "../components/ResumeUpload/ResumeUpload.jsx";
import { api } from "../services/api.js";

const STAGES = [
  "Reading resumes…",
  "Extracting skills…",
  "Comparing with job description…",
  "Calculating match scores…",
];

export default function Screening() {
  const navigate = useNavigate();
  const [job, setJob] = useState({ title: "", description: "", file: null, scoringWeights: null });
  const [resumeFiles, setResumeFiles] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [stageIndex, setStageIndex] = useState(0);
  const intervalRef = useRef(null);

  useEffect(() => () => clearInterval(intervalRef.current), []);

  const jdReady = job.file || job.description.trim().length > 0;
  const canSubmit = jdReady && resumeFiles.length > 0 && !loading;

  async function handleSubmit() {
    setError("");
    setLoading(true);
    setStageIndex(0);
    intervalRef.current = setInterval(() => {
      setStageIndex((i) => Math.min(i + 1, STAGES.length - 1));
    }, 900);

    try {
      const createdJob = await api.createJob({
        title: job.title,
        description: job.description,
        file: job.file,
        scoringWeights: job.scoringWeights,
      });
      await api.screenBulk(createdJob.job_id, resumeFiles);
      navigate(`/results/${createdJob.job_id}`);
    } catch (err) {
      setError(err.message || "Something went wrong while screening.");
      setLoading(false);
      clearInterval(intervalRef.current);
    }
  }

  if (loading) {
    return <LoadingState stage={STAGES[stageIndex]} />;
  }

  return (
    <div className="page-enter workflow-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">New workspace / 02</p>
          <h1>Build a screening</h1>
          <p className="subtitle">Set the brief, add your candidate pool, and let the evidence shape the shortlist.</p>
        </div>
        <span className="step-counter">01 <i /> 02 <i /> 03</span>
      </div>
      <p className="subtitle">Provide a job description and one or more resumes to screen against it.</p>

      {error && <div className="error-banner">{error}</div>}

      <div className="workflow-grid">
        <JobDescriptionInput value={job} onChange={setJob} />
        <ResumeUpload files={resumeFiles} onFilesChange={setResumeFiles} />
      </div>

      <div className="action-row">
        <button type="button" className="btn btn-primary" disabled={!canSubmit} onClick={handleSubmit}>
          Run screening <span aria-hidden="true">-&gt;</span>
        </button>
        <span className="action-note">{resumeFiles.length || 0} resume{resumeFiles.length === 1 ? "" : "s"} ready</span>
      </div>
      {!jdReady && <p className="muted">Add a job description to continue.</p>}
      {jdReady && resumeFiles.length === 0 && <p className="muted">Add at least one resume to continue.</p>}
    </div>
  );
}
