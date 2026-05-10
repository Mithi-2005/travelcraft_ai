import { motion } from "framer-motion";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuthContext } from "../../state/AuthContext";

function AppShell({ children }) {
  const navigate = useNavigate();
  const { user, logout } = useAuthContext();
  const navItems = user
    ? [
        { label: "Home", to: "/" },
        { label: "Dashboard", to: "/dashboard" },
        { label: "Generator", to: "/generator" },
        { label: "Memory", to: "/memory" },
      ]
    : [
        { label: "Home", to: "/" },
        { label: "Login", to: "/login" },
        { label: "Register", to: "/register" },
      ];

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="noise-overlay" />
      <div className="ambient-ring left-[-8rem] top-10 h-72 w-72 bg-glow/20" />
      <div className="ambient-ring bottom-0 right-[-10rem] h-80 w-80 bg-coral/20" />
      <header className="fixed inset-x-0 top-0 z-50">
        <div className="mx-auto flex max-w-[1280px] items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            className="lux-panel flex items-center gap-3 px-4 py-3"
          >
            <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-glow via-aqua to-solar p-[1px]">
              <div className="flex h-full w-full items-center justify-center rounded-lg bg-ink font-display text-lg font-bold">
                T
              </div>
            </div>
            <div>
              <p className="font-display text-sm font-bold tracking-[0.2em] text-white">TRAVELCRAFT AI</p>
              <p className="text-xs text-white/55">Memory-driven trip design</p>
            </div>
          </motion.div>

          <div className="flex items-center gap-3">
            <nav className="lux-panel hidden items-center gap-2 px-3 py-2 md:flex">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `rounded-full px-4 py-2 text-sm font-medium transition ${
                      isActive ? "bg-white text-ink" : "text-white/72 hover:bg-white/[0.07]"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>

            {user ? (
              <div className="lux-panel hidden items-center gap-4 px-4 py-3 md:flex">
                <div className="text-right">
                  <p className="text-sm font-semibold text-white">{user.name}</p>
                  <p className="text-xs text-white/50">{user.email}</p>
                </div>
                <button type="button" className="button-secondary" onClick={handleLogout}>
                  Logout
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </header>

      {children}

      <nav className="fixed inset-x-4 bottom-4 z-50 md:hidden">
        <div
          className="lux-panel grid gap-2 px-2 py-2"
          style={{ gridTemplateColumns: `repeat(${navItems.length}, minmax(0, 1fr))` }}
        >
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `rounded-lg px-3 py-3 text-center text-xs font-semibold transition ${
                  isActive ? "bg-white text-ink" : "text-white/70"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      </nav>

      {user ? (
        <button
          type="button"
          className="button-secondary fixed right-4 top-[5.5rem] z-50 md:hidden"
          onClick={handleLogout}
        >
          Logout
        </button>
      ) : null}
    </div>
  );
}

export default AppShell;
