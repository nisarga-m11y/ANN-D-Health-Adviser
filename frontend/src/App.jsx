import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import Navbar from "./components/Navbar";
import AppErrorBoundary from "./components/AppErrorBoundary";
import ProtectedRoute from "./components/ProtectedRoute";
import ChatbotDashboard from "./pages/ChatbotDashboard";
import HealthReportPage from "./pages/HealthReportPage";
import HomePage from "./pages/HomePage";
import OtpAuthPage from "./pages/OtpAuthPage";
import RegisterPage from "./pages/RegisterPage";

function App() {
  const location = useLocation();
  const hideNavbar = location.pathname === "/dashboard";

  return (
    <AppErrorBoundary>
      {!hideNavbar && <Navbar />}
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<OtpAuthPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <ChatbotDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/health-report"
          element={
            <ProtectedRoute>
              <HealthReportPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppErrorBoundary>
  );
}

export default App;

