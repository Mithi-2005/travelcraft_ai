import { Navigate } from "react-router-dom";
import { PanelSkeleton } from "../ui/LoadingSkeleton";
import { useAuthContext } from "../../state/AuthContext";

function GuestRoute({ children }) {
  const { user, loadingSession } = useAuthContext();

  if (loadingSession) {
    return (
      <div className="page-shell">
        <PanelSkeleton className="h-[420px]" />
      </div>
    );
  }

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

export default GuestRoute;
