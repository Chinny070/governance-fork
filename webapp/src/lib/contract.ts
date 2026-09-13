// ---------------------------------------------------------------------------
// Canonical production deployment.
//
// Stage 10 (steward-requested fixes: fork adjudication context, required
// source evidence, envelope-submitter binding, two-step finality commit).
// Contract source: commit 91601b2 of contracts/governance_fork.py
// SHA-256: 0068ab5f87490774333e5a1aed90b39e827b2b1936895d08b9ec94c7ebdf39ef
// Deployed manually to GenLayer StudioNet; schema verified 36 methods
// (17 write + 17 view + 2 admin), lock_bond the sole payable method.
//
// Previous production address (commit 004dbd4, pre-Stage-10):
// 0xbA06003F2C254232E4D440B89425abc7Afd4c11A -- superseded, do not use.
// ---------------------------------------------------------------------------

export const CONTRACT_ADDRESS =
  "0x4ACb76E0517a3Ad2d19699486595291b0089b077" as const;

export const CONTRACT_SOURCE_COMMIT = "91601b2" as const;
export const CONTRACT_SOURCE_SHA256 =
  "0068ab5f87490774333e5a1aed90b39e827b2b1936895d08b9ec94c7ebdf39ef" as const;

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
