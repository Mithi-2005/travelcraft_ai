import { AnimatePresence } from "framer-motion";
import { Route, Routes, useLocation } from "react-router-dom";
import GuestRoute from "./components/auth/GuestRoute";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import AppShell from "./components/shell/AppShell";
import PageTransition from "./components/shell/PageTransition";
import CustomCursor from "./components/ui/CustomCursor";
import DashboardPage from "./pages/DashboardPage";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import MemoryPage from "./pages/MemoryPage";
import RegisterPage from "./pages/RegisterPage";
import TripDetailPage from "./pages/TripDetailPage";
import TripGeneratorPage from "./pages/TripGeneratorPage";

function App() {
  const location = useLocation();

  return (
    <>
      <CustomCursor />
      <AppShell>
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route
              path="/"
              element={
                <PageTransition>
                  <LandingPage />
                </PageTransition>
              }
            />
            <Route
              path="/dashboard"
              element={
                <PageTransition>
                  <ProtectedRoute>
                    <DashboardPage />
                  </ProtectedRoute>
                </PageTransition>
              }
            />
            <Route
              path="/generator"
              element={
                <PageTransition>
                  <ProtectedRoute>
                    <TripGeneratorPage />
                  </ProtectedRoute>
                </PageTransition>
              }
            />
            <Route
              path="/memory"
              element={
                <PageTransition>
                  <ProtectedRoute>
                    <MemoryPage />
                  </ProtectedRoute>
                </PageTransition>
              }
            />
            <Route
              path="/trip/:tripId"
              element={
                <PageTransition>
                  <ProtectedRoute>
                    <TripDetailPage />
                  </ProtectedRoute>
                </PageTransition>
              }
            />
            <Route
              path="/login"
              element={
                <PageTransition>
                  <GuestRoute>
                    <LoginPage />
                  </GuestRoute>
                </PageTransition>
              }
            />
            <Route
              path="/register"
              element={
                <PageTransition>
                  <GuestRoute>
                    <RegisterPage />
                  </GuestRoute>
                </PageTransition>
              }
            />
          </Routes>
        </AnimatePresence>
      </AppShell>
    </>
  );
}

export default App;
