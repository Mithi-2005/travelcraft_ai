function SectionHeading({ eyebrow, title, body, align = "left" }) {
  return (
    <div className={align === "center" ? "mx-auto max-w-2xl text-center" : "max-w-2xl"}>
      <p className="eyebrow">{eyebrow}</p>
      <h2 className="mt-4 font-display text-3xl font-bold tracking-[-0.05em] text-white sm:text-5xl">
        {title}
      </h2>
      {body ? <p className="mt-4 text-sm leading-7 text-white/60 sm:text-base">{body}</p> : null}
    </div>
  );
}

export default SectionHeading;
