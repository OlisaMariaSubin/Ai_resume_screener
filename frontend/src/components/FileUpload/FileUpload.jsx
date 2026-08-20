export default function FileUpload({ id, label, accept, onFile, selectedName }) {
  return (
    <div className="field">
      {label && <span className="file-picker-label">{label}</span>}
      <label className="file-picker" htmlFor={id}>
        <span className="file-picker-icon" aria-hidden="true">+</span>
        <span>{selectedName || "Choose a file"}</span>
        <span className="file-picker-action">Browse</span>
      </label>
      <input
        className="file-input-hidden"
        id={id}
        type="file"
        accept={accept}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
        }}
      />
      {selectedName && <p className="muted">Selected: {selectedName}</p>}
    </div>
  );
}
