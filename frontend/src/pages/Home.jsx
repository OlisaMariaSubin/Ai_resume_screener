import { useNavigate } from "react-router-dom";

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="home-hero page-enter">
      <div className="hero-copy">
        <p className="eyebrow">Recruiting operations / 01</p>
        <h1>Find the signal<br /><em>inside every resume.</em></h1>
        <p className="subtitle">
          Turn a job description and a stack of resumes into a clear, explainable shortlist. Every score shows its work.
        </p>
        <div className="home-actions">
          <button type="button" className="btn btn-primary" onClick={() => navigate("/screen")}>
            Start a screening <span aria-hidden="true">-&gt;</span>
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => navigate("/screen?bulk=1")}>
            Screen a batch
          </button>
        </div>
      </div>
      <div className="hero-rail" aria-label="Workflow overview">
        <span className="rail-number">01</span>
        <div>
          <strong>Brief</strong>
          <p>Parse the role and define what matters.</p>
        </div>
        <span className="rail-line" />
        <span className="rail-number">02</span>
        <div>
          <strong>Compare</strong>
          <p>Match skills, experience, and language.</p>
        </div>
        <span className="rail-line" />
        <span className="rail-number">03</span>
        <div>
          <strong>Decide</strong>
          <p>Review a ranked, transparent shortlist.</p>
        </div>
      </div>
    </div>
  );
}
