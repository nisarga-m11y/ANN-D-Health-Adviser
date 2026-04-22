import { useEffect, useMemo, useState } from "react";

import { fetchChatHistory } from "../api/chat";

function HealthReportPage() {
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadHistory() {
      try {
        const data = await fetchChatHistory();
        setHistory(data);
      } catch {
        setError("Could not load report data.");
      }
    }

    loadHistory();
  }, []);

  const diseaseCounts = useMemo(() => {
    return history.reduce((acc, item) => {
      const key = item.predicted_disease || "Unknown";
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});
  }, [history]);

  return (
    <main className="container report-page">
      <h2>Health Report</h2>
      <p>Your latest chatbot analysis history is summarized below.</p>

      {error && <p className="error-text">{error}</p>}

      <section className="card">
        <h3>Disease Prediction Summary</h3>
        {Object.keys(diseaseCounts).length === 0 ? (
          <p>No prediction history yet.</p>
        ) : (
          <ul className="summary-list">
            {Object.entries(diseaseCounts).map(([disease, count]) => (
              <li key={disease}>
                <strong>{disease}</strong>: {count} case(s)
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h3>Recent Advice Log</h3>
        {history.length === 0 ? (
          <p>No advice available.</p>
        ) : (
          <div className="history-list">
            {history.slice(0, 10).map((item) => (
              <article key={item.id} className="history-item">
                <p><strong>Symptom input:</strong> {item.message}</p>
                <p><strong>Prediction:</strong> {item.predicted_disease}</p>
                <p><strong>Advice:</strong> {item.advice}</p>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

export default HealthReportPage;
