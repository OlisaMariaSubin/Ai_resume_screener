import { useNavigate } from "react-router-dom";

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="home-hero">
      <h1>Screen resumes against a job description — transparently.</h1>
      <p className="subtitle">
        Upload a job description and one or more resumes. Get a match score, matched and missing skills, and a
        ranked shortlist — with every number explained, never a black box.
      </p>
      <div className="home-actions">
        <button type="button" className="btn btn-primary" onClick={() => navigate("/screen")}>
          Start Screening
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => navigate("/screen?bulk=1")}>
          Bulk Screening
        </button>
      </div>
    </div>
  );
}
