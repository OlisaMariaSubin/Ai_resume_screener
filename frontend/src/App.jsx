import { Route, Routes } from "react-router-dom";
import Home from "./pages/Home.jsx";
import Results from "./pages/Results.jsx";
import Screening from "./pages/Screening.jsx";

export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <a href="/" className="brand">
            <span className="brand-mark">AI</span> Resume Screening Assistant
          </a>
        </div>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/screen" element={<Screening />} />
          <Route path="/results/:jobId" element={<Results />} />
        </Routes>
      </main>
    </div>
  );
}
