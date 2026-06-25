import { Routes, Route, Navigate } from "react-router-dom";
import Home from "./pages/Home";
import AnalysisPage from "./pages/AnalysisPage";
import ReportPage from "./pages/ReportPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/analyze/:sessionId" element={<AnalysisPage />} />
      <Route path="/report/:sessionId" element={<ReportPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
