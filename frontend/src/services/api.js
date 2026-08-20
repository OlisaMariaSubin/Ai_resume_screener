const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  let response;
  // Ensure no double slashes or missing slashes between base URL and path
  const cleanBase = API_BASE_URL.replace(/\/+$/, "");
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const targetUrl = `${cleanBase}${cleanPath}`;

  try {
    response = await fetch(targetUrl, options);
  } catch (err) {
    throw new ApiError("Could not reach the server. Is the backend running?", 0);
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // response had no JSON body
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return null;
  return response.json();
}

export const api = {
  health: () => request("/health"),

  parseJobDescription: ({ file, description }) => {
    if (file) {
      const form = new FormData();
      form.append("file", file);
      return request("/api/jobs/parse-preview", { method: "POST", body: form });
    }
    return request("/api/jobs/parse-preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description }),
    });
  },

  createJob: ({ title, description, file, scoringWeights }) => {
    if (file) {
      const form = new FormData();
      form.append("title", title || "");
      form.append("file", file);
      if (scoringWeights) form.append("scoring_weights", JSON.stringify(scoringWeights));
      return request("/api/jobs", { method: "POST", body: form });
    }
    return request("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description, scoring_weights: scoringWeights || undefined }),
    });
  },

  getJob: (jobId) => request(`/api/jobs/${jobId}`),

  getResumeContent: (resumeId) => request(`/api/resumes/${resumeId}/content`),

  updateJob: (jobId, { title, description, scoringWeights }) =>
    request(`/api/jobs/${jobId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        description,
        scoring_weights: scoringWeights || undefined,
      }),
    }),

  uploadResume: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/api/resumes", { method: "POST", body: form });
  },

  screenSingle: (jobId, resumeId) =>
    request("/api/screen", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: jobId, resume_id: resumeId }),
    }),

  screenBulk: (jobId, files) => {
    const form = new FormData();
    form.append("job_id", jobId);
    files.forEach((file) => form.append("files", file));
    return request("/api/screen/bulk", { method: "POST", body: form });
  },

  getResults: (jobId, skills) => {
    const query = skills && skills.length ? `?skills=${encodeURIComponent(skills.join(","))}` : "";
    return request(`/api/screen/${jobId}/results${query}`);
  },

  rerunScreening: (jobId) => request(`/api/screen/${jobId}/rerun`, { method: "POST" }),

  explainScore: (jobId, resumeId) =>
    request(`/api/screen/${jobId}/${resumeId}/explain`, { method: "POST" }),

  getAudit: (jobId) => request(`/api/screen/${jobId}/audit`),

  getTrends: (jobId) => request(`/api/screen/${jobId}/trends`),

  downloadExcel: async (jobId) => {
    let response;
    const cleanBase = API_BASE_URL.replace(/\/+$/, "");
    try {
      response = await fetch(`${cleanBase}/api/screen/${jobId}/export/excel`);
    } catch (err) {
      throw new ApiError("Could not reach the server. Is the backend running?", 0);
    }
    if (!response.ok) {
      let detail = `Request failed (${response.status})`;
      try {
        const body = await response.json();
        detail = body.detail || detail;
      } catch {
        // response had no JSON body
      }
      throw new ApiError(detail, response.status);
    }

    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/);
    const filename = match ? match[1] : `screening_results_${jobId}.xlsx`;

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
};

export { ApiError };