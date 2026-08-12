interface EligibilityBadgeProps {
  eligible: boolean;
}

export default function EligibilityBadge({ eligible }: EligibilityBadgeProps) {
  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
        eligible
          ? "bg-emerald-100 text-emerald-800"
          : "bg-rose-100 text-rose-800"
      }`}
    >
      {eligible ? "Eligible" : "Not Eligible"}
    </span>
  );
}
