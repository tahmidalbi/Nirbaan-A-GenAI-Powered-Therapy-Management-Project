import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

const ProtectedRoute = ({ children, allowedRoles }) => {
  const { isAuthenticated, user, _hasHydrated } = useAuthStore();

  // Debug logs
  console.log('ProtectedRoute - hasHydrated:', _hasHydrated);
  console.log('ProtectedRoute - isAuthenticated:', isAuthenticated);
  console.log('ProtectedRoute - user:', user);
  console.log('ProtectedRoute - user role:', user?.role);
  console.log('ProtectedRoute - allowedRoles:', allowedRoles);

  // Wait for hydration to complete
  if (!_hasHydrated) {
    console.log('ProtectedRoute - Waiting for hydration...');
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    console.log('ProtectedRoute - Not authenticated, redirecting to /login');
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    console.log('ProtectedRoute - Role not allowed, redirecting to /');
    return <Navigate to="/" replace />;
  }

  console.log('ProtectedRoute - Access granted');
  return children;
};

export default ProtectedRoute;