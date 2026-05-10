import { useEffect, useRef } from "react";
import * as THREE from "three";

function WorldGlobe({ className = "" }) {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, container.clientWidth / container.clientHeight, 0.1, 100);
    camera.position.z = 8;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8));
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    const group = new THREE.Group();
    scene.add(group);

    const globeGeometry = new THREE.SphereGeometry(2.1, 34, 34);
    const wireframe = new THREE.LineSegments(
      new THREE.WireframeGeometry(globeGeometry),
      new THREE.LineBasicMaterial({ color: 0x68ffe5, transparent: true, opacity: 0.22 }),
    );
    group.add(wireframe);

    const pointsGeometry = new THREE.BufferGeometry();
    const pointPositions = [];
    for (let i = 0; i < 950; i += 1) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const radius = 2.12;
      pointPositions.push(
        radius * Math.sin(phi) * Math.cos(theta),
        radius * Math.sin(phi) * Math.sin(theta),
        radius * Math.cos(phi),
      );
    }
    pointsGeometry.setAttribute("position", new THREE.Float32BufferAttribute(pointPositions, 3));
    const points = new THREE.Points(
      pointsGeometry,
      new THREE.PointsMaterial({
        color: 0xffffff,
        size: 0.04,
        transparent: true,
        opacity: 0.9,
      }),
    );
    group.add(points);

    const routeMaterial = new THREE.LineBasicMaterial({ color: 0xff8f72, transparent: true, opacity: 0.9 });
    const arcs = [
      [
        new THREE.Vector3(-1.7, 0.2, 0.9),
        new THREE.Vector3(-0.4, 2.5, 1.6),
        new THREE.Vector3(1.4, 0.3, 1.2),
      ],
      [
        new THREE.Vector3(-0.9, -1.2, 1.4),
        new THREE.Vector3(0.4, 1.8, 2.2),
        new THREE.Vector3(1.8, -0.1, 0.6),
      ],
      [
        new THREE.Vector3(-1.1, 1.1, -1),
        new THREE.Vector3(0.3, 2.3, 0.5),
        new THREE.Vector3(1.7, 0.8, -1),
      ],
    ];

    arcs.forEach((arc) => {
      const curve = new THREE.QuadraticBezierCurve3(arc[0], arc[1], arc[2]);
      const curvePoints = curve.getPoints(64);
      const geometry = new THREE.BufferGeometry().setFromPoints(curvePoints);
      const line = new THREE.Line(geometry, routeMaterial);
      group.add(line);
    });

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    const pointLight = new THREE.PointLight(0x00ffc6, 4.5, 30);
    pointLight.position.set(4, 2, 6);
    scene.add(ambientLight, pointLight);

    let pointerX = 0;
    let pointerY = 0;
    const onPointerMove = (event) => {
      const rect = container.getBoundingClientRect();
      pointerX = ((event.clientX - rect.left) / rect.width - 0.5) * 0.6;
      pointerY = ((event.clientY - rect.top) / rect.height - 0.5) * 0.4;
    };

    const clock = new THREE.Clock();
    let frameId = 0;
    const animate = () => {
      const elapsed = clock.getElapsedTime();
      group.rotation.y += 0.0038;
      group.rotation.x = THREE.MathUtils.lerp(group.rotation.x, pointerY, 0.04);
      group.rotation.z = THREE.MathUtils.lerp(group.rotation.z, pointerX, 0.04);
      points.material.opacity = 0.62 + Math.sin(elapsed * 1.8) * 0.18;
      renderer.render(scene, camera);
      frameId = requestAnimationFrame(animate);
    };

    const onResize = () => {
      if (!container) return;
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };

    window.addEventListener("resize", onResize);
    container.addEventListener("pointermove", onPointerMove);
    animate();

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener("resize", onResize);
      container.removeEventListener("pointermove", onPointerMove);
      renderer.dispose();
      container.removeChild(renderer.domElement);
      globeGeometry.dispose();
      pointsGeometry.dispose();
    };
  }, []);

  return <div className={className} ref={containerRef} />;
}

export default WorldGlobe;
