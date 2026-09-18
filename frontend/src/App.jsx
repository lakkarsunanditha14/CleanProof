import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import PlaceholderPage from './pages/PlaceholderPage';

export default function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route
            path="/report"
            element={
              <PlaceholderPage
                title="Report Issue"
                description="Submit a civic complaint with photo and location."
              />
            }
          />
          <Route
            path="/track"
            element={
              <PlaceholderPage
                title="Track Complaints"
                description="Search and check status of existing complaints."
              />
            }
          />
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
