import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <main className="container auth-page">
        <div className="auth-card" role="status" aria-live="polite">
          <h2 style={{ marginTop: 0 }}>Loading your session...</h2>
          <p style={{ marginBottom: 0 }}>We are checking your login status.</p>
        </div>
      </main>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

export default ProtectedRoute;
