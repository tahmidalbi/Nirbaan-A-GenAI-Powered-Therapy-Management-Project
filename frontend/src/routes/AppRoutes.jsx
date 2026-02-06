import { Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from '../pages/LandingPage';
import Login from '../auth/Login';
import Signup from '../auth/Signup';
import ProtectedRoute from '../auth/ProtectedRoute';
import PatientDashboard from '../dashboards/PatientDashboard';
import TherapistDashboard from '../dashboards/TherapistDashboard';
import EmergencyDashboard from '../dashboards/EmergencyDashboard';

const AppRoutes = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      
      {/* Protected Routes - Patient */}
      <Route
        path="/patient/dashboard"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <PatientDashboard />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Therapist */}
      <Route
        path="/therapist/dashboard"
        element={
          <ProtectedRoute allowedRoles={['therapist']}>
            <TherapistDashboard />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Emergency Handler */}
      <Route
        path="/emergency/dashboard"
        element={
          <ProtectedRoute allowedRoles={['emergency']}>
            <EmergencyDashboard />
          </ProtectedRoute>
        }
      />

      {/* Redirect unknown routes to landing page */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default AppRoutes;
