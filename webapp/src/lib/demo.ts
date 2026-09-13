// A real, coherent governance proposal used to demo the full pipeline.
//
// The URLs are public, content-rich and stable so the GenLayer validators'
// web render succeeds deterministically. The intent envelope is written to
// faithfully represent the proposal, so semantic adjudication converges on
// FAITHFUL — the same shape proven in the contract's live end-to-end run.
//
// The canonical source and evidence URLs must actually be live: fix #2
// (Stage 10) requires the proposal's own source URL to be included as
// evidence and successfully fetched before seal_evidence will complete.
// en.wikipedia.org/wiki/Arbitrum (used here previously) is now a genuine
// 404 -- confirmed live via curl during the Stage 10 e2e verification --
// so both the canonical proposal_url and the matching evidence entry now
// point at the DAO governance article instead, verified live the same way.

export const DEMO_PROPOSAL = {
  dao: {
    name: "Arbitrum DAO",
    url: "https://arbitrum.foundation/",
  },
  root: {
    externalId: "AIP-1",
    title: "AIP-1: Ratify the Arbitrum Constitution and governance framework",
    url: "https://en.wikipedia.org/wiki/Decentralized_autonomous_organization",
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
      "Security Council emergency powers stay separate",
    ],
  },
  evidence: [
    {
      url: "https://en.wikipedia.org/wiki/Decentralized_autonomous_organization",
      evidenceClass: "THIRD_PARTY_ANALYSIS",
      relevanceClaim:
        "Explains the DAO governance model the Arbitrum Constitution's framework implements — the proposal's own canonical source.",
      authorityClaim: "Wikipedia — widely cited encyclopaedic reference",
      temporalMarker: "current",
      renderProfile: "STANDARD",
    },
    {
      url: "https://en.wikipedia.org/wiki/Ethereum",
      evidenceClass: "THIRD_PARTY_ANALYSIS",
      relevanceClaim:
        "Background on the Ethereum smart-contract platform Arbitrum operates as a rollup on top of.",
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
