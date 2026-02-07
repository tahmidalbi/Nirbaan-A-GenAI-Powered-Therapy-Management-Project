import { Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from '../pages/LandingPage';
import RoleSelection from '../pages/RoleSelection';
import Login from '../auth/Login';
import Signup from '../auth/Signup';
import PatientLogin from '../auth/PatientLogin';
import EmergencyPersonnelLogin from '../auth/EmergencyPersonnelLogin';
import ProtectedRoute from '../auth/ProtectedRoute';
import PatientDashboard from '../dashboards/PatientDashboard';
import OCDPatientDashboard from '../dashboards/OCDPatientDashboard';
import ADHDPatientDashboard from '../dashboards/ADHDPatientDashboard';
import PatientDetail from '../pages/PatientDetail';
import TherapistDashboard from '../dashboards/TherapistDashboard';
import EmergencyPersonnelDashboard from '../dashboards/EmergencyPersonnelDashboard';
import EmergencyPersonnelDetail from '../pages/EmergencyPersonnelDetail';

const AppRoutes = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/select-role" element={<RoleSelection />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/patient/login" element={<PatientLogin />} />
      <Route path="/emergency-personnel/login" element={<EmergencyPersonnelLogin />} />
      
      {/* Protected Routes - Patient */}
      <Route
        path="/patient/dashboard"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <PatientDashboard />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Patient OCD Dashboard */}
      <Route
        path="/patient/dashboard/ocd"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <OCDPatientDashboard />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Patient ADHD Dashboard */}
      <Route
        path="/patient/dashboard/adhd"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <ADHDPatientDashboard />
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

      {/* Protected Routes - Therapist Patient Detail */}
      <Route
        path="/therapist/patients/:patientId"
        element={
          <ProtectedRoute allowedRoles={['therapist']}>
            <PatientDetail />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Therapist Emergency Personnel Detail */}
      <Route
        path="/therapist/emergency-personnel/:personnelId"
        element={
          <ProtectedRoute allowedRoles={['therapist']}>
            <EmergencyPersonnelDetail />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Emergency Personnel */}
      <Route
        path="/emergency-personnel/dashboard"
        element={
          <ProtectedRoute allowedRoles={['emergency_personnel']}>
            <EmergencyPersonnelDashboard />
          </ProtectedRoute>
        }
      />

      {/* Redirect unknown routes to landing page */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default AppRoutes;
