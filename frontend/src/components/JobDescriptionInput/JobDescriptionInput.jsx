import { useState } from "react";
import FileUpload from "../FileUpload/FileUpload.jsx";
import ScoringWeightsPanel from "../ScoringWeightsPanel/ScoringWeightsPanel.jsx";
import { api } from "../../services/api.js";

export default function JobDescriptionInput({ value, onChange, showWeights = true }) {
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState("");
  const [inputMode, setInputMode] = useState("paste");

  async function handleFileUpload(file) {
    setParseError("");
    setParsing(true);
    try {
      const preview = await api.parseJobDescription({ file });
      onChange({
        ...value,
        file,
        title: value.title || preview.title || "",
        description: preview.description,
      });
      setInputMode("paste");
    } catch (err) {
      setParseError(err.message || "Could not read the uploaded file.");
    } finally {
      setParsing(false);
    }
  }

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

      <div className="input-mode" role="tablist" aria-label="Job description input method">
        <button
          type="button"
          className={inputMode === "paste" ? "active" : ""}
          onClick={() => setInputMode("paste")}
        >
          Paste description
        </button>
        <button
          type="button"
          className={inputMode === "upload" ? "active" : ""}
          onClick={() => setInputMode("upload")}
        >
          Upload file
        </button>
      </div>

      {inputMode === "upload" ? (
        <div className="jd-upload-panel">
          <FileUpload
            id="job-file"
            label="Upload PDF, DOCX, or TXT"
            accept=".pdf,.docx,.txt"
            selectedName={value.file?.name}
            onFile={handleFileUpload}
          />
          <p className="muted">We will extract the text and open it for review before screening.</p>
          {parsing && <p className="muted">Extracting text from file…</p>}
          {parseError && <p className="error-text">{parseError}</p>}
        </div>
      ) : (
        <div className="field">
          <label htmlFor="job-description">Job description text</label>
          <p className="muted" style={{ marginTop: 0 }}>
            Paste the role details, including Required/Must-have and Preferred/Nice-to-have sections.
          </p>
          <textarea
            id="job-description"
            value={value.description}
            onChange={(e) => onChange({ ...value, description: e.target.value, file: null })}
            placeholder="Paste the full job description here..."
          />
        </div>
      )}

      {showWeights && (
        <ScoringWeightsPanel weights={value.scoringWeights} onChange={(w) => onChange({ ...value, scoringWeights: w })} />
      )}
    </div>
  );
}
