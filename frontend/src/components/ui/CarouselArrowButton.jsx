function ChevronIcon({ direction }) {
  const rotation = direction === "left" ? "rotate(180 10 10)" : undefined;

  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 20 20"
      fill="none"
      className="h-4 w-4"
    >
      <path
        d="M7 4.5L12.5 10L7 15.5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        transform={rotation}
      />
    </svg>
  );
}

function CarouselArrowButton({ direction, label, onClick, className = "" }) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className={`carousel-arrow ${className}`.trim()}
    >
      <ChevronIcon direction={direction} />
    </button>
  );
}

export default CarouselArrowButton;
