// Governance Fork mark — a stem that diverges. Geometric lines only.
// Uses currentColor; the stem is ink, the branch node is the caller's accent.

export function Mark({
  size = 22,
  className,
  branchColor = "var(--coral)",
}: {
  size?: number;
  className?: string;
  branchColor?: string;
}) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      {/* stem */}
      <path
        d="M6 3 V21"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      {/* upper branch */}
      <path
        d="M6 9 H13 Q17 9 17 13 V15"
        stroke={branchColor}
        strokeWidth="1.7"
        strokeLinecap="round"
        fill="none"
      />
      {/* lower branch */}
      <path
        d="M6 15 H11"
        stroke={branchColor}
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      {/* nodes */}
      <circle cx="6" cy="3.4" r="2" fill="currentColor" />
      <circle cx="17" cy="16.4" r="2" fill={branchColor} />
      <circle cx="13" cy="15" r="1.7" fill={branchColor} />
      <circle cx="6" cy="20.6" r="2" fill="currentColor" />
    </svg>
  );
}

export function Brand({ onClick }: { onClick?: () => void }) {
  return (
    <button className="brand" onClick={onClick} aria-label="Governance Fork — home">
      <Mark className="mark" size={22} />
      <span className="name">Governance&nbsp;Fork</span>
    </button>
  );
}
