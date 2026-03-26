import { Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from '../pages/LandingPage';
import RoleSelection from '../pages/RoleSelection';
import Login from '../auth/Login';
import Signup from '../auth/Signup';
import PatientLogin from '../auth/PatientLogin';
import EmergencyPersonnelLogin from '../auth/EmergencyPersonnelLogin';
import ProtectedRoute from '../auth/ProtectedRoute';
import PatientDashboard from '../dashboards/PatientDashboard';
import OCDTools from '../dashboards/OCDPatientDashboard';
import PatientAssessmentPage from '../pages/PatientAssessmentPage';
import PatientOCDEducation from '../pages/PatientOCDEducation';
import PatientDetail from '../pages/PatientDetail';
import PatientWeeklyProgress from '../pages/PatientWeeklyProgress';
import TherapistDashboard from '../dashboards/TherapistDashboard';
import TherapistToolsPage from '../dashboards/TherapistToolsPage';
import PatientSelfMonitoring from '../components/PatientSelfMonitoring';
import TherapistSelfMonitoringView from '../components/TherapistSelfMonitoringView';
import PatientFearLadderHub from '../pages/PatientFearLadderHub';
import PatientFearLadderEducation from '../pages/PatientFearLadderEducation';
import PatientFearLadderPage from '../pages/PatientFearLadderPage';
import PatientFearLadderMonitoring from '../pages/PatientFearLadderMonitoring';
import TherapistFearLadderHub from '../pages/TherapistFearLadderHub';
import TherapistFearLadderPatientList from '../pages/TherapistFearLadderPatientList';
import TherapistFearLadderPatientView from '../pages/TherapistFearLadderPatientView';
import TherapistFearLadderMonitoring from '../pages/TherapistFearLadderMonitoring';
import EmergencyPersonnelDashboard from '../dashboards/EmergencyPersonnelDashboard';
import EmergencyPersonnelDetail from '../pages/EmergencyPersonnelDetail';
import VideoSession from '../pages/VideoSession';
import ERPWorkspace from '../pages/ERPWorkspace';
import ERPPlanRecovery from '../pages/ERPPlanRecovery';
import ERPDiveIn from '../pages/ERPDiveIn';
import ERPSessionPage from '../pages/ERPSessionPage';
import ERPAIReport from '../pages/ERPAIReport';
import TherapistERPPatientList from '../pages/TherapistERPPatientList';
import TherapistERPObsessionList from '../pages/TherapistERPObsessionList';
import TherapistERPObsessionView from '../pages/TherapistERPObsessionView';
import NirbaanAIChat from '../pages/NirbaanAIChat';
import TherapistNirbaanAIPage from '../pages/TherapistNirbaanAIPage';
import TherapistChatPage from '../pages/TherapistChatPage';
import PatientChatPage from '../pages/PatientChatPage';
import EPChatPage from '../pages/EPChatPage';

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

      {/* Protected Routes - Patient OCD Tools */}
      <Route
        path="/patient/dashboard/tools/ocd"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <OCDTools />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Patient Assessment */}
      <Route
        path="/patient/dashboard/tools/ocd/assessment"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <PatientAssessmentPage />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - OCD Core Education */}
      <Route
        path="/patient/dashboard/tools/ocd/assessment/ocd-education"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <PatientOCDEducation />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Patient Self Monitoring */}
      <Route
        path="/patient/dashboard/self-monitoring"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <PatientSelfMonitoring />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Patient Weekly Progress */}
      <Route
        path="/patient/dashboard/progress"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <PatientWeeklyProgress />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Patient Fear Ladder Hub */}
      <Route
        path="/patient/dashboard/fear-ladder"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <PatientFearLadderHub />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Patient Fear Ladder Education */}
      <Route
        path="/patient/dashboard/fear-ladder/education"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <PatientFearLadderEducation />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Patient Fear Ladder Builder */}
      <Route
        path="/patient/dashboard/fear-ladder/builder"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <PatientFearLadderPage />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Patient Fear Ladder Monitoring */}
      <Route
        path="/patient/dashboard/fear-ladder/monitoring"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <PatientFearLadderMonitoring />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - ERP Workspace */}
      <Route
        path="/patient/dashboard/erp"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <ERPWorkspace />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - ERP Plan Recovery */}
      <Route
        path="/patient/dashboard/erp/plan"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <ERPPlanRecovery />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - ERP Dive In */}
      <Route
        path="/patient/dashboard/erp/dive-in"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <ERPDiveIn />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - ERP Session */}
      <Route
        path="/patient/dashboard/erp/session/:itemId"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <ERPSessionPage />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - ERP AI Report */}
      <Route
        path="/patient/dashboard/erp/item/:itemId/ai-report"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <ERPAIReport />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - NirbaanAI Chat */}
      <Route
        path="/patient/nirbaanai"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <NirbaanAIChat />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Therapist NirbaanAI */}
      <Route
        path="/therapist/nirbaanai"
        element={
          <ProtectedRoute allowedRoles={['therapist']}>
            <TherapistNirbaanAIPage />
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

      {/* Protected Routes - Therapist Tools */}
      <Route
        path="/therapist/dashboard/tools"
        element={
          <ProtectedRoute allowedRoles={['therapist']}>
            <TherapistToolsPage />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Therapist ERP Patient List */}
      <Route
        path="/therapist/dashboard/erp"
        element={
          <ProtectedRoute allowedRoles={['therapist']}>
            <TherapistERPPatientList />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Therapist ERP Obsession List (one patient) */}
      <Route
        path="/therapist/dashboard/erp/patient/:patientId"
        element={
          <ProtectedRoute allowedRoles={['therapist']}>
            <TherapistERPObsessionList />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Therapist ERP Obsession Detail (split panel) */}
      <Route
        path="/therapist/dashboard/erp/patient/:patientId/item/:itemId"
        element={
          <ProtectedRoute allowedRoles={['therapist']}>
            <TherapistERPObsessionView />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Therapist Self Monitoring View */}
      <Route
        path="/therapist/dashboard/self-monitoring"
        element={
          <ProtectedRoute allowedRoles={['therapist']}>
            <TherapistSelfMonitoringView />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Therapist Fear Ladder Hub */}
      <Route
        path="/therapist/dashboard/fear-ladder"
        element={
          <ProtectedRoute allowedRoles={['therapist']}>
            <TherapistFearLadderHub />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Therapist Fear Ladder Patient List */}
      <Route
        path="/therapist/dashboard/fear-ladder/patients"
        element={
          <ProtectedRoute allowedRoles={['therapist']}>
            <TherapistFearLadderPatientList />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Therapist Fear Ladder Patient View */}
      <Route
        path="/therapist/dashboard/fear-ladder/patient/:patientId"
        element={
          <ProtectedRoute allowedRoles={['therapist']}>
            <TherapistFearLadderPatientView />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Therapist Fear Ladder Monitoring */}
      <Route
        path="/therapist/dashboard/fear-ladder/monitoring"
        element={
          <ProtectedRoute allowedRoles={['therapist']}>
            <TherapistFearLadderMonitoring />
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

      {/* Protected Routes - Video Call/Session */}
      <Route
        path="/video-session/:userType/:userId/:patientId"
        element={
          <ProtectedRoute allowedRoles={['therapist', 'patient']}>
            <VideoSession />
          </ProtectedRoute>
        }
      />

      <Route
        path="/video-call/:sessionId"
        element={
          <ProtectedRoute allowedRoles={['therapist', 'patient']}>
            <VideoSession />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Chat Pages */}
      <Route
        path="/therapist/chat"
        element={
          <ProtectedRoute allowedRoles={['therapist']}>
            <TherapistChatPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/patient/chat"
        element={
          <ProtectedRoute allowedRoles={['patient']}>
            <PatientChatPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/emergency/chat"
        element={
          <ProtectedRoute allowedRoles={['emergency_personnel']}>
            <EPChatPage />
          </ProtectedRoute>
        }
      />

      {/* Redirect unknown routes to landing page */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default AppRoutes;
