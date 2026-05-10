import { Navigate, useLocation } from "react-router-dom";
import { PanelSkeleton } from "../ui/LoadingSkeleton";
import { useAuthContext } from "../../state/AuthContext";

function ProtectedRoute({ children }) {
  const location = useLocation();
  const { user, loadingSession } = useAuthContext();

  if (loadingSession) {
    return (
      <div className="page-shell">
        <PanelSkeleton className="h-[420px]" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}

export default ProtectedRoute;
