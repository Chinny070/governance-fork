import type { GenLayerClient } from "./genlayer";

// A tiny module-level holder for the connected write client, kept in sync by
// WalletProvider. Lets terse inline action handlers reach the client without
// threading it through every component. Reads/UI still go through hooks.

let active: GenLayerClient | null = null;

export function setActiveWriteClient(c: GenLayerClient | null) {
  active = c;
}

export function getActiveWriteClient(): GenLayerClient {
  if (!active) {
    throw new Error(
      "No wallet connected. Connect a wallet on StudioNet to submit this transaction.",
    );
  }
  return active;
}

export function hasActiveWriteClient(): boolean {
  return active !== null;
}
