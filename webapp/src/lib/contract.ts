// ---------------------------------------------------------------------------
// Canonical production deployment.
//
// Stage 10 (steward-requested fixes: fork adjudication context, required
// source evidence, envelope-submitter binding, AND a real enforced-duration
// finality challenge period -- gl.message_raw["datetime"] is a genuine,
// consensus-safe on-chain timestamp on this runtime, live-proven end to
// end; see docs/STAGE_10_STEWARD_FIXES.md section 4).
// Stage 11 (adoption signalling, creator reputation, escalated final
// appeal; additive on Stage 10). Previous production: 0xD5A1E3b2087d439C36571B50947ddD900741f143
// (commit 019630d) -- superseded, do not use.
// Stage 11 fix: creator-reputation keys lowercased (previous deployment
// 0x74e066e148A24581D17E0F8dC539cE9EC7410B8D, commit fe762c4,
// always read zero reputation) -- superseded, do not use.
// Contract source: commit 586ab80 of contracts/governance_fork.py
// SHA-256: 64cd82bfcafcea208523b5b46f1c9a257b9d443bb31483288fd57f15e1f44aaf
// Deployed manually to GenLayer StudioNet; schema verified 42 methods
// (20 write + 20 view + 2 admin), lock_bond the sole payable method.
//
// Previous production address (commit 91601b2, two-step commit without a
// real enforced duration): 0x4ACb76E0517a3Ad2d19699486595291b0089b077
// -- superseded, do not use.
// Earlier still (commit 004dbd4, pre-Stage-10):
// 0xbA06003F2C254232E4D440B89425abc7Afd4c11A -- superseded, do not use.
// ---------------------------------------------------------------------------

export const CONTRACT_ADDRESS =
  "0x0CEAe8A2c86aC2DBf5b5CC5B4CC67f0e9b5D9299" as const;

export const CONTRACT_SOURCE_COMMIT = "586ab80" as const;
export const CONTRACT_SOURCE_SHA256 =
  "64cd82bfcafcea208523b5b46f1c9a257b9d443bb31483288fd57f15e1f44aaf" as const;

// genlayer-js network key (see genlayer-js/chains). StudioNet.
export const GENLAYER_NETWORK = "studionet" as const;

// StudioNet chain parameters — used for wallet network detection and for
// the "add / switch network" prompt.
export const STUDIONET = {
  chainIdDec: 61999,
  chainIdHex: "0xf22f", // 61999
  chainName: "GenLayer Studionet",
  rpcUrl: "https://studio.genlayer.com/api",
  nativeCurrency: { name: "GEN", symbol: "GEN", decimals: 18 },
  // genlayer-explorer.vercel.app (the previous value here) now returns
  // 503 -- explorer-studio.genlayer.com is GenLayer's own current Studio
  // explorer (confirmed working, and the format their own Project
  // Explorer submission form expects for contract links).
  explorerBase: "https://explorer-studio.genlayer.com",
} as const;

export function explorerTxUrl(hash: string): string {
  return `${STUDIONET.explorerBase}/tx/${hash}`;
}

export function explorerAddressUrl(addr: string): string {
  return `${STUDIONET.explorerBase}/address/${addr}`;
}

export const REPO_URL =
  "https://github.com/Chinny070/governance-fork" as const;
