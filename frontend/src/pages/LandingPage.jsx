import { motion, useScroll, useTransform } from "framer-motion";
import gsap from "gsap";
import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import MagneticButton from "../components/ui/MagneticButton";
import SectionHeading from "../components/ui/SectionHeading";
import WorldGlobe from "../components/ui/WorldGlobe";
import { useAuthContext } from "../state/AuthContext";

const features = [
  {
    title: "Live destination intelligence",
    body: "Firecrawl surfaces current local texture, cost signals, and high-intent places so each itinerary is grounded in what is happening now.",
    accent: "from-glow/50 to-aqua/20",
  },
  {
    title: "Memento memory engine",
    body: "TravelCraft remembers budgets, moods, interests, and trip history, then turns those memories into better future recommendations.",
    accent: "from-coral/40 to-solar/20",
  },
  {
    title: "LLM-crafted pacing",
    body: "Plans are generated as elegant, day-wise narratives instead of dumped lists, with believable timing, mood continuity, and spend guidance.",
    accent: "from-iris/40 to-glow/20",
  },
];

const testimonials = [
  {
    quote: "It feels like a luxury concierge crossed with a design studio.",
    author: "Mina, Product Lead",
  },
  {
    quote: "The trip mood control changed everything. It understood how I wanted the city to feel.",
    author: "Daniel, Founder",
  },
  {
    quote: "Finally a planner that remembers what I loved last time.",
    author: "Isha, Creative Director",
  },
];

function LandingPage() {
  const { user } = useAuthContext();
  const heroRef = useRef(null);
  const badgeRef = useRef(null);
  const titleRef = useRef(null);
  const copyRef = useRef(null);
  const ctaRef = useRef(null);

  const { scrollYProgress } = useScroll();
  const globeY = useTransform(scrollYProgress, [0, 1], [0, -120]);

  useEffect(() => {
    const ctx = gsap.context(() => {
      const timeline = gsap.timeline({ defaults: { ease: "power3.out" } });
      timeline
        .fromTo(badgeRef.current, { opacity: 0, y: 32 }, { opacity: 1, y: 0, duration: 0.8 })
        .fromTo(titleRef.current, { opacity: 0, y: 42 }, { opacity: 1, y: 0, duration: 0.9 }, "-=0.45")
        .fromTo(copyRef.current, { opacity: 0, y: 28 }, { opacity: 1, y: 0, duration: 0.8 }, "-=0.5")
        .fromTo(ctaRef.current, { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.8 }, "-=0.45");
    }, heroRef);
    return () => ctx.revert();
  }, []);

  return (
    <div className="page-shell">
      <section ref={heroRef} className="grid items-center gap-10 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="relative">
          <div ref={badgeRef} className="pill w-fit">
            <span className="h-2 w-2 rounded-full bg-glow shadow-[0_0_18px_rgba(0,255,198,0.9)]" />
            Personalized trip planning with memory + live data
          </div>
          <h1 ref={titleRef} className="headline mt-6 max-w-4xl">
            Build journeys that feel composed, not generated.
          </h1>
          <p ref={copyRef} className="subcopy mt-6">
            TravelCraft AI blends Firecrawl research, LLM itinerary design, and a Memento memory layer
            into a planning experience that feels cinematic, calm, and deeply personal.
          </p>

          <div ref={ctaRef} className="mt-8 flex flex-col gap-4 sm:flex-row">
            <MagneticButton as={Link} to={user ? "/generator" : "/register"} className="button-primary">
              {user ? "Plan Your Trip" : "Create Your Account"}
            </MagneticButton>
            <MagneticButton as={Link} to={user ? "/dashboard" : "/login"} className="button-secondary">
              {user ? "Explore Dashboard" : "Sign In"}
            </MagneticButton>
          </div>

          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            {[
              ["96%", "preference match score"],
              ["4 days", "default cinematic itinerary"],
              ["live", "destination signal enrichment"],
            ].map(([value, label]) => (
              <div key={label} className="soft-panel px-5 py-4">
                <p className="font-display text-3xl font-bold tracking-[-0.06em] text-white">{value}</p>
                <p className="mt-2 text-sm text-white/58">{label}</p>
              </div>
            ))}
          </div>
        </div>

        <motion.div style={{ y: globeY }} className="relative h-[520px]">
          <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-white/[0.06] to-white/[0.02] blur-3xl" />
          <div className="lux-panel absolute inset-0 overflow-hidden p-6">
            <div className="absolute left-8 top-8 rounded-full border border-white/10 bg-black/30 px-4 py-2 text-xs text-white/70">
              Travel paths rendered in motion
            </div>
            <WorldGlobe className="h-full w-full" />
            <div className="absolute bottom-8 left-8 max-w-[220px] rounded-lg border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
              <p className="text-xs uppercase tracking-[0.28em] text-white/50">Trip mood</p>
              <p className="mt-2 font-display text-2xl font-bold text-glow">Relaxed</p>
              <p className="mt-2 text-sm text-white/58">Sunset pacing, shorter transit, long dinners, neighborhood-first routing.</p>
            </div>
            <div className="absolute right-8 top-24 w-[240px] rounded-lg border border-white/10 bg-white/[0.08] p-4 backdrop-blur-xl">
              <p className="eyebrow">Live Suggestions</p>
              <div className="mt-3 space-y-3">
                {["Riverside market crawl", "Late booking alert for rooftop table", "Design hotel cluster near tram line"].map((item) => (
                  <div key={item} className="rounded-lg border border-white/8 bg-black/30 px-3 py-3 text-sm text-white/72">
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      <section className="mt-28">
        <SectionHeading
          eyebrow="Core Stack"
          title="A planning engine built around memory, live research, and mood-driven pacing."
          body="Every layer does a different job: real-time discovery, preference recall, and itinerary orchestration. The result feels less like a form and more like a travel director."
        />
        <div className="mt-10 grid gap-6 lg:grid-cols-3">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 36 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.55, delay: index * 0.08 }}
              className="lux-panel relative overflow-hidden p-6"
            >
              <div className={`absolute inset-x-4 top-0 h-24 rounded-b-full bg-gradient-to-r ${feature.accent} blur-3xl`} />
              <p className="eyebrow relative">0{index + 1}</p>
              <h3 className="relative mt-5 font-display text-2xl font-bold tracking-[-0.05em]">{feature.title}</h3>
              <p className="relative mt-4 text-sm leading-7 text-white/62">{feature.body}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="mt-28 grid gap-8 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="soft-panel p-8">
          <SectionHeading
            eyebrow="Interactive Preview"
            title="See how the world map turns into a plan."
            body="A subtle 3D surface, route pulses, and recommendation layers make the product feel spatial before you ever hit generate."
          />
          <div className="mt-8 space-y-4">
            {[
              "AI Trip Mood selector tunes energy, luxury, and tempo.",
              "Animated timeline shows how each day unfolds.",
              "Smart suggestions adapt from stored past trips.",
            ].map((item) => (
              <div key={item} className="pill w-full justify-start border-white/12 bg-white/[0.04] px-4 py-3 text-sm">
                <span className="h-2 w-2 rounded-full bg-coral" />
                {item}
              </div>
            ))}
          </div>
        </div>

        <div className="lux-panel relative min-h-[420px] overflow-hidden p-6 sm:p-8">
          <div className="mb-6 grid grid-cols-4 gap-2">
            {["Input", "Research", "Plan", "Save"].map((label, index) => (
              <div key={label} className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-center">
                <p className="text-xs font-semibold text-white/72">{label}</p>
                <div
                  className={`mx-auto mt-2 h-1 rounded-full ${
                    index === 0 ? "bg-glow" : index === 1 ? "bg-coral" : index === 2 ? "bg-solar" : "bg-iris"
                  }`}
                />
              </div>
            ))}
          </div>
          <div className="relative grid gap-4 md:grid-cols-2">
            {[
              ["Morning", "Mercado stop, ceramic atelier, tram-side espresso"],
              ["Afternoon", "Museum quarter pause, boutique hotel reset, riverside lunch"],
              ["Evening", "Sunset lookout, chef-led tasting, after-dark jazz room"],
              ["Budget", "INR 53,000 premium daily pacing with room for signature moments"],
            ].map(([label, text]) => (
              <div key={label} className="rounded-lg border border-white/10 bg-black/35 p-5 backdrop-blur-xl">
                <p className="eyebrow">{label}</p>
                <p className="mt-3 text-sm leading-7 text-white/68">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mt-28">
        <SectionHeading
          eyebrow="Loved By Explorers"
          title="Testimonials that sound like people describing a service, not a feature list."
          align="center"
        />
        <div className="mt-10 grid gap-6 lg:grid-cols-3">
          {testimonials.map((item, index) => (
            <motion.div
              key={item.author}
              initial={{ opacity: 0, y: 26 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1, duration: 0.55 }}
              className="soft-panel p-6"
            >
              <p className="font-display text-2xl leading-tight tracking-[-0.04em] text-white/92">"{item.quote}"</p>
              <p className="mt-6 text-sm uppercase tracking-[0.24em] text-white/45">{item.author}</p>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default LandingPage;
