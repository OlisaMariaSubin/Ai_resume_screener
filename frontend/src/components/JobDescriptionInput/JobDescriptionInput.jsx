import { useState } from "react";
import FileUpload from "../FileUpload/FileUpload.jsx";
import ScoringWeightsPanel from "../ScoringWeightsPanel/ScoringWeightsPanel.jsx";

export default function JobDescriptionInput({ value, onChange }) {
  const [mode, setMode] = useState("paste");

  return (
    <div className="card">
      <h2>Job description</h2>

      <div className="field">
        <label htmlFor="job-title">Job title</label>
        <input
          id="job-title"
          type="text"
          value={value.title}
          onChange={(e) => onChange({ ...value, title: e.target.value })}
          placeholder="e.g. Backend Engineer Intern"
        />
      </div>

      <div className="tabs">
        <button type="button" className={`tab-btn ${mode === "paste" ? "active" : ""}`} onClick={() => setMode("paste")}>
          Paste text
        </button>
        <button type="button" className={`tab-btn ${mode === "upload" ? "active" : ""}`} onClick={() => setMode("upload")}>
          Upload file
        </button>
      </div>

      {mode === "paste" ? (
        <div className="field">
          <label htmlFor="job-description">Job description text</label>
          <textarea
            id="job-description"
            value={value.description}
            onChange={(e) => onChange({ ...value, description: e.target.value, file: null })}
            placeholder="Paste the full job description here, including a Required/Must-have section and an optional Preferred/Nice-to-have section."
          />
        </div>
      ) : (
        <FileUpload
          id="job-file"
          label="Upload PDF, DOCX, or TXT"
          accept=".pdf,.docx,.txt"
          selectedName={value.file?.name}
          onFile={(file) => onChange({ ...value, file, description: "" })}
        />
      )}

      <ScoringWeightsPanel weights={value.scoringWeights} onChange={(w) => onChange({ ...value, scoringWeights: w })} />
    </div>
  );
}
