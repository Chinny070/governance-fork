// ---------------------------------------------------------------------------
// Canonical production deployment.
//
// Contract source: commit 004dbd4 of contracts/governance_fork.py
// SHA-256: dfe6ebc85cbb38ae1d7a4dcc07924af0facaa819c87289e4fe838c12e7c6e5f5
// Deployed manually to GenLayer StudioNet; schema verified 35 methods
// (16 write + 17 view + 2 admin), lock_bond the sole payable method.
// ---------------------------------------------------------------------------

export const CONTRACT_ADDRESS =
  "0xbA06003F2C254232E4D440B89425abc7Afd4c11A" as const;

export const CONTRACT_SOURCE_COMMIT = "004dbd4" as const;
export const CONTRACT_SOURCE_SHA256 =
  "dfe6ebc85cbb38ae1d7a4dcc07924af0facaa819c87289e4fe838c12e7c6e5f5" as const;

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
  explorerBase: "https://genlayer-explorer.vercel.app",
} as const;

export function explorerTxUrl(hash: string): string {
  return `${STUDIONET.explorerBase}/tx/${hash}`;
}

export function explorerAddressUrl(addr: string): string {
  return `${STUDIONET.explorerBase}/address/${addr}`;
}

export const REPO_URL =
  "https://github.com/Chinny070/governance-fork" as const;
