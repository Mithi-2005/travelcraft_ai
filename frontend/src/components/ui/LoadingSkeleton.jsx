export function PanelSkeleton({ className = "" }) {
  return <div className={`soft-panel shimmer min-h-[220px] ${className}`} />;
}

export function PlanSkeleton() {
  return (
    <div className="space-y-4">
      <div className="soft-panel shimmer h-40" />
      <div className="grid gap-4 md:grid-cols-2">
        <div className="soft-panel shimmer h-48" />
        <div className="soft-panel shimmer h-48" />
      </div>
      <div className="soft-panel shimmer h-64" />
    </div>
  );
}
