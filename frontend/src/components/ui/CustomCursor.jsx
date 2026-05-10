import { motion } from "framer-motion";
import { useEffect, useState } from "react";

function CustomCursor() {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [active, setActive] = useState(false);

  useEffect(() => {
    const onMove = (event) => setPosition({ x: event.clientX, y: event.clientY });
    const onOver = (event) => {
      setActive(Boolean(event.target.closest("[data-cursor='active']")));
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseover", onOver);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseover", onOver);
    };
  }, []);

  return (
    <>
      <motion.div
        className="cursor-dot"
        animate={{ x: position.x, y: position.y, scale: active ? 0.4 : 1 }}
        transition={{ type: "spring", damping: 24, stiffness: 380, mass: 0.4 }}
      />
      <motion.div
        className="cursor-ring"
        animate={{
          x: position.x,
          y: position.y,
          scale: active ? 1.8 : 1,
          borderColor: active ? "rgba(0,255,198,0.8)" : "rgba(255,255,255,0.5)",
        }}
        transition={{ type: "spring", damping: 26, stiffness: 280, mass: 0.7 }}
      />
    </>
  );
}

export default CustomCursor;
