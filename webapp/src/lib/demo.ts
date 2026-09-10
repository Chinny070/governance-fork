// A real, coherent governance proposal used to demo the full pipeline.
//
// The URLs are public, content-rich and stable so the GenLayer validators'
// web render succeeds deterministically. The intent envelope is written to
// faithfully represent the proposal, so semantic adjudication converges on
// FAITHFUL — the same shape proven in the contract's live end-to-end run.

export const DEMO_PROPOSAL = {
  dao: {
    name: "Arbitrum DAO",
    url: "https://arbitrum.foundation/",
  },
  root: {
    externalId: "AIP-1",
    title: "AIP-1: Ratify the Arbitrum Constitution and governance framework",
    url: "https://en.wikipedia.org/wiki/Arbitrum",
    params: [
      ["framework", "Arbitrum Constitution"],
      ["governed_chains", "Arbitrum One, Arbitrum Nova"],
      ["governance_token", "ARB"],
      ["security_council_size", "12"],
    ] as [string, string][],
  },
  envelope: {
    objective:
      "Ratify the Arbitrum Constitution as the foundational governance framework for the Arbitrum DAO, establishing token-holder control over Arbitrum One and Arbitrum Nova, the powers and limits of the DAO, and the role of the Security Council.",
    beneficiaryClass: "ARB token holders and Arbitrum network users",
    resourceType: "POLICY",
    scope:
      "Adoption of the constitutional text and governance process for the Arbitrum DAO; does not itself move treasury funds.",
    essentialConstraints: [
      "Token holders retain ultimate control of governance decisions",
      "The Security Council may act only within powers the Constitution grants it",
      "Constitutional changes require the defined on-chain governance process",
    ],
    mutableDimensions: [
      "proposal thresholds and voting periods",
      "treasury allocation policy",
      "grant program design",
    ],
    immutableDimensions: [
      "token-holder ultimate authority",
      "separation of Security Council emergency powers from routine governance",
    ],
  },
  evidence: [
    {
      url: "https://en.wikipedia.org/wiki/Arbitrum",
      evidenceClass: "THIRD_PARTY_ANALYSIS",
      relevanceClaim:
        "Independent overview of Arbitrum, its DAO, the ARB token and the Constitution's role.",
      authorityClaim: "Wikipedia — widely cited encyclopaedic reference",
      temporalMarker: "current",
      renderProfile: "STANDARD",
    },
    {
      url: "https://en.wikipedia.org/wiki/Decentralized_autonomous_organization",
      evidenceClass: "THIRD_PARTY_ANALYSIS",
      relevanceClaim:
        "Explains the DAO governance model the proposal's framework implements.",
      authorityClaim: "Wikipedia",
      temporalMarker: "current",
      renderProfile: "STANDARD",
    },
  ],
};

// A pre-written fork of the demo proposal — narrows a mutable dimension
// without touching an immutable one, so it adjudicates FAITHFUL.
export const DEMO_FORK = {
  title: "Fork: fixed 3-day minimum voting period",
  summary:
    "Keeps the Arbitrum Constitution framework intact but pins the routine-proposal voting period to a 3-day minimum for predictability.",
  reasoning:
    "Voting periods are an explicitly mutable dimension of the envelope. Setting a floor does not alter token-holder authority or the Security Council's separation of powers, so the parent intent is preserved.",
  delta: [
    {
      dimension_name: "proposal thresholds and voting periods",
      parent_value: "voting periods set by governance process",
      fork_value: "routine proposals: 3-day minimum voting period",
      claim_kind: "NARROWED",
    },
  ],
};
