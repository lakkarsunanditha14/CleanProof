import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import ReportPage from './pages/ReportPage';
import TrackPage from './pages/TrackPage';
import WorkerPage from './pages/WorkerPage';
import ReviewPage from './pages/ReviewPage';
import DashboardPage from './pages/DashboardPage';

export default function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/report" element={<ReportPage />} />
          <Route path="/track" element={<TrackPage />} />
          <Route path="/worker" element={<WorkerPage />} />
          <Route path="/review" element={<ReviewPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </Layout>
    </Router>
  );
}
