import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import PlaceholderPage from './pages/PlaceholderPage';
import ReportPage from './pages/ReportPage';
import TrackPage from './pages/TrackPage';

export default function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/report" element={<ReportPage />} />
          <Route path="/track" element={<TrackPage />} />
          <Route
            path="/worker"
            element={
              <PlaceholderPage
                title="Municipal Worker Panel"
                description="Upload after-photos and mark issues resolved."
              />
            }
          />
          <Route
            path="/review"
            element={
              <PlaceholderPage
                title="Verification Review Queue"
                description="Audit flagged suspicious and fake resolution reports."
              />
            }
          />
          <Route
            path="/dashboard"
            element={
              <PlaceholderPage
                title="SLA & Fraud Dashboard"
                description="Analytics on SLA adherence, false closures, and ward statistics."
              />
            }
          />
        </Routes>
      </Layout>
    </Router>
  );
}
