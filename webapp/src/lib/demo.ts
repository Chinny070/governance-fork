// A real, coherent governance proposal used to demo the full pipeline.
//
// This is EIP-1559 (Ethereum's fee-market reform), written up against
// ethereum.org's official gas and blocks documentation. The envelope's
// mutable/immutable split is stated explicitly in the proposal's own text
// (docs/demo/eip-1559-proposal.md): the base fee is set by the protocol and
// burned (immutable), the priority fee is a user-set tip (mutable). With no
// source declaring that split, the adjudicator reasonably answers UNCLEAR on
// DIMENSION_CLASSIFICATION about half the time; stating it explicitly fixes that.
//
// The canonical source and evidence URLs must be live and must actually
// discuss the proposal: the contract requires the proposal's own source URL to
// be included as evidence and fetched before seal_evidence completes, and the
// adjudicator judges the envelope against what those pages really say.

const GAS = "https://ethereum.org/en/developers/docs/gas/";
const PROPOSAL_DOC =
  "https://raw.githubusercontent.com/Chinny070/governance-fork/main/docs/demo/eip-1559-proposal.md";

export const DEMO_PROPOSAL = {
  dao: {
    name: "Ethereum Fee Market DAO",
    url: "https://ethereum.org/",
  },
  root: {
    externalId: "EIP-1559",
    title: "EIP-1559: fee market reform with a burned base fee",
    url: PROPOSAL_DOC,
    params: [
      ["base_fee_burned", "true"],
      ["base_fee_max_change_percent", "12.5"],
      ["priority_fee_tip_gwei", "2"],
    ] as [string, string][],
  },
  envelope: {
    objective:
      "Reform Ethereum's transaction fee market so each block has a protocol-set base fee that adjusts with demand and is burned, while users add a priority tip of their own choosing that is paid to validators.",
    beneficiaryClass: "Ethereum users and ETH holders",
    resourceType: "PROTOCOL_PARAMETER",
    scope:
      "Transaction fee mechanics only; does not change the issuance schedule or the consensus rules beyond fee handling.",
    essentialConstraints: [
      "The base fee is set by the protocol and is burned, not paid to validators",
      "The priority tip is set by each user and is paid to the validator",
    ],
    mutableDimensions: ["priority_fee_tip_gwei"],
    immutableDimensions: ["base_fee_burned", "base_fee_max_change_percent"],
  },
  evidence: [
    {
      url: PROPOSAL_DOC,
      evidenceClass: "OFFICIAL_GOVERNANCE",
      relevanceClaim:
        "The proposal's own text: states the fee design and explicitly which dimensions are immutable and which are mutable.",
      authorityClaim: "The proposal document itself",
      temporalMarker: "current",
      renderProfile: "STANDARD",
    },
    {
      url: GAS,
      evidenceClass: "OFFICIAL_DOCUMENTATION",
      relevanceClaim:
        "Official Ethereum documentation of the gas and base-fee mechanism introduced by EIP-1559.",
      authorityClaim: "ethereum.org",
      temporalMarker: "current",
      renderProfile: "STANDARD",
    },
  ],
};

// A pre-written fork of the demo proposal. It changes only the mutable,
// user-set priority tip and leaves the protocol-set, burned base fee alone;
// the same shape was adjudicated FAITHFUL live.
export const DEMO_FORK = {
  title: "Fork: suggested priority tip 3 gwei",
  summary:
    "Keeps the EIP-1559 design (protocol-set burned base fee, user-set priority tip) and only changes priority_fee_tip_gwei from 2 to 3.",
  reasoning:
    "priority_fee_tip_gwei is the user-set priority tip, an explicitly mutable dimension; changing it leaves the protocol-set, burned base fee untouched, so the original intent is preserved.",
  params: [
    ["base_fee_burned", "true"],
    ["base_fee_max_change_percent", "12.5"],
    ["priority_fee_tip_gwei", "3"],
  ] as [string, string][],
  delta: [
    {
      dimension_name: "priority_fee_tip_gwei",
      parent_value: "2",
      fork_value: "3",
      claim_kind: "RESHAPED",
    },
  ],
};
