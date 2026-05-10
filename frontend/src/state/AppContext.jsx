import { createContext, startTransition, useContext, useEffect, useMemo, useState } from "react";
import { ApiError, generateTrip, getUserMemory, updateUserMemory } from "../lib/api";
import { useAuthContext } from "./AuthContext";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const { user, loadingSession, clearAuthState, refreshSession } = useAuthContext();
  const [memory, setMemory] = useState(null);
  const [loadingMemory, setLoadingMemory] = useState(true);
  const [memoryError, setMemoryError] = useState("");
  const [recentPlan, setRecentPlan] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const refreshMemory = async () => {
    if (!user) {
      setMemory(null);
      setRecentPlan(null);
      setLoadingMemory(false);
      setMemoryError("");
      return null;
    }

    setLoadingMemory(true);
    setMemoryError("");
    try {
      const data = await getUserMemory();
      startTransition(() => {
        setMemory(data);
      });
      return data;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        const restoredUser = await refreshSession();
        if (restoredUser) {
          try {
            const retryData = await getUserMemory();
            startTransition(() => {
              setMemory(retryData);
            });
            return retryData;
          } catch (retryError) {
            if (!(retryError instanceof ApiError && retryError.status === 401)) {
              setMemoryError(retryError.message || "Unable to load memory.");
              return null;
            }
          }
        }
        clearAuthState();
        setMemory(null);
        setRecentPlan(null);
        return null;
      }
      setMemoryError(error.message || "Unable to load memory.");
      return null;
    } finally {
      setLoadingMemory(false);
    }
  };

  useEffect(() => {
    if (loadingSession) return;
    refreshMemory();
  }, [user, loadingSession]);

  const saveMemory = async (payload) => {
    try {
      const updated = await updateUserMemory(payload);
      setMemory(updated);
      return updated;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        clearAuthState();
        setMemory(null);
        setRecentPlan(null);
      }
      throw error;
    }
  };

  const createTrip = async (payload) => {
    setIsGenerating(true);
    try {
      const plan = await generateTrip(payload);
      setRecentPlan(plan);
      await refreshMemory();
      return plan;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        clearAuthState();
        setMemory(null);
        setRecentPlan(null);
      }
      throw error;
    } finally {
      setIsGenerating(false);
    }
  };

  const value = useMemo(
    () => ({
      memory,
      loadingMemory,
      memoryError,
      recentPlan,
      isGenerating,
      refreshMemory,
      saveMemory,
      createTrip,
    }),
    [memory, loadingMemory, memoryError, recentPlan, isGenerating],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useAppContext must be used inside AppProvider");
  }
  return context;
}
