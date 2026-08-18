export default function FileUpload({ id, label, accept, onFile, selectedName }) {
  return (
    <div className="field">
      {label && <label htmlFor={id}>{label}</label>}
      <input
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
