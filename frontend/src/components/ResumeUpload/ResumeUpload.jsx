import { useRef, useState } from "react";

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ResumeUpload({ files, onFilesChange }) {
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef(null);

  function addFiles(fileList) {
    const incoming = Array.from(fileList).filter((f) => /\.(pdf|docx)$/i.test(f.name));
    onFilesChange([...files, ...incoming]);
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragActive(false);
    addFiles(e.dataTransfer.files);
  }

  function removeFile(index) {
    onFilesChange(files.filter((_, i) => i !== index));
  }

  return (
    <div className="card">
      <h2>Resumes</h2>
      <div
        className={`dropzone ${dragActive ? "active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        Drag and drop resume files here, or click to browse (PDF or DOCX, multiple allowed)
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          multiple
          hidden
          onChange={(e) => addFiles(e.target.files)}
        />
      </div>

      {files.length > 0 && (
        <ul className="file-list">
          {files.map((file, i) => (
            <li className="file-row" key={`${file.name}-${i}`}>
              <span>
                {file.name} <span className="muted">({formatSize(file.size)})</span>
              </span>
              <span>
                <span className="file-status pending">ready</span>
                <button
                  type="button"
                  className="btn btn-ghost"
                  style={{ marginLeft: 8, padding: "2px 8px" }}
                  onClick={() => removeFile(i)}
                >
                  Remove
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
