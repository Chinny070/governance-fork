// A real, coherent governance proposal used to demo the full pipeline.
//
// This is EIP-1559 (Ethereum's fee-market reform), written up against
// ethereum.org's official gas and blocks documentation. The same data was run
// live on StudioNet and the root, and two forks of it, were adjudicated
// FAITHFUL -- unlike generic or off-topic evidence, which the adjudicator
// correctly returns UNCLEAR for (it cannot confirm claims the sources never
// make).
//
// The canonical source and evidence URLs must be live and must actually
// discuss the proposal: the contract requires the proposal's own source URL to
// be included as evidence and fetched before seal_evidence completes, and the
// adjudicator judges the envelope against what those pages really say.

const GAS = "https://ethereum.org/en/developers/docs/gas/";
const BLOCKS = "https://ethereum.org/en/developers/docs/blocks/";

export const DEMO_PROPOSAL = {
  dao: {
    name: "Ethereum Fee Market DAO",
    url: "https://ethereum.org/",
  },
  root: {
    externalId: "EIP-1559",
    title: "EIP-1559: fee market reform with a burned base fee",
    url: GAS,
    params: [
      ["base_fee_max_change_denominator", "8"],
      ["elasticity_multiplier", "2"],
      ["base_fee_burned", "true"],
    ] as [string, string][],
  },
  envelope: {
    objective:
      "Reform Ethereum's transaction fee market so each block has a protocol-set base fee that adjusts with demand and is burned, with users adding a priority tip for block producers, and blocks able to flex around a target size.",
    beneficiaryClass: "Ethereum users and ETH holders",
    resourceType: "PROTOCOL_PARAMETER",
    scope:
      "Transaction fee mechanics only; does not change the issuance schedule or the consensus rules beyond fee handling.",
    essentialConstraints: [
      "The base fee is burned and not paid to block producers",
      "Users may add a priority tip paid to block producers",
    ],
    mutableDimensions: [
      "elasticity_multiplier",
      "base_fee_max_change_denominator",
    ],
    immutableDimensions: ["base_fee_burned"],
  },
  evidence: [
    {
      url: GAS,
      evidenceClass: "OFFICIAL_DOCUMENTATION",
      relevanceClaim:
        "Official Ethereum documentation of the gas and base-fee mechanism introduced by EIP-1559 — the proposal's own canonical source.",
      authorityClaim: "ethereum.org",
      temporalMarker: "current",
      renderProfile: "STANDARD",
    },
    {
      url: BLOCKS,
      evidenceClass: "OFFICIAL_DOCUMENTATION",
      relevanceClaim:
        "Official documentation of blocks and the variable block size target.",
      authorityClaim: "ethereum.org",
      temporalMarker: "current",
      renderProfile: "STANDARD",
    },
  ],
};

// A pre-written fork of the demo proposal. It retunes one explicitly mutable
// parameter and leaves the immutable one (the burn) alone; the same shape was
// adjudicated FAITHFUL live.
export const DEMO_FORK = {
  title: "Fork: elasticity multiplier 3",
  summary:
    "Keeps the EIP-1559 design (burned base fee, priority tip) and only retunes elasticity_multiplier from 2 to 3.",
  reasoning:
    "elasticity_multiplier is an explicitly mutable tuning parameter; changing it does not touch burning of the base fee or the tip, so the original intent is preserved.",
  delta: [
    {
      dimension_name: "elasticity_multiplier",
      parent_value: "2",
      fork_value: "3",
      claim_kind: "RESHAPED",
    },
  ],
};
