import { motion, useMotionValue, useSpring } from "framer-motion";

function MagneticButton({ as: Component = "button", className = "", children, ...props }) {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, { stiffness: 180, damping: 14, mass: 0.4 });
  const springY = useSpring(y, { stiffness: 180, damping: 14, mass: 0.4 });

  const onMove = (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    x.set((event.clientX - rect.left - rect.width / 2) * 0.18);
    y.set((event.clientY - rect.top - rect.height / 2) * 0.18);
  };

  const onLeave = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <motion.div style={{ x: springX, y: springY }} onMouseMove={onMove} onMouseLeave={onLeave}>
      <Component data-cursor="active" className={className} {...props}>
        {children}
      </Component>
    </motion.div>
  );
}

export default MagneticButton;
