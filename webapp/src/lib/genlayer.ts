// genlayer-js client layer.
//
// Two clients:
//   - read client  : no account, used for every view call and for polling
//                     authoritative state. Works with no wallet connected.
//   - write client : bound to the connected EOA + window.ethereum, used for
//                    every state-changing call.
//
// Call shapes mirror the working CLI reference (scratchpad/gjs.mjs) exactly:
//   client.readContract({ address, functionName, args })
//   client.writeContract({ address, functionName, args, value })
//   client.waitForTransactionReceipt({ hash, status })

import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionStatus } from "genlayer-js/types";
import { CONTRACT_ADDRESS, GENLAYER_NETWORK } from "./contract";

export type GenLayerClient = ReturnType<typeof createClient>;

export interface EthereumProvider {
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
  on?: (event: string, handler: (...a: unknown[]) => void) => void;
  removeListener?: (event: string, handler: (...a: unknown[]) => void) => void;
  isMetaMask?: boolean;
}

declare global {
  interface Window {
    ethereum?: EthereumProvider;
  }
}

export function getInjectedProvider(): EthereumProvider | undefined {
  return typeof window !== "undefined" ? window.ethereum : undefined;
}

// ---- errors -----------------------------------------------------------------

/** The contract executed but reverted (gl.vm.UserError). State did not change. */
export class ContractRevertError extends Error {
  constructor(public reason: string) {
    super(reason);
    this.name = "ContractRevertError";
  }
}

/** Validators could not agree (Undetermined). Zero state committed; retry. */
export class UndeterminedError extends Error {
  constructor(message = "Validators did not reach consensus (Undetermined).") {
    super(message);
    this.name = "UndeterminedError";
  }
}

// ---- read client (singleton) ----------------------------------------------
let _readClient: GenLayerClient | null = null;

export function readClient(): GenLayerClient {
  if (!_readClient) {
    _readClient = createClient({ chain: studionet });
  }
  return _readClient;
}

// ---- write client (per connected account) --------------------------------
export function makeWriteClient(account: string): GenLayerClient {
  const provider = getInjectedProvider();
  if (!provider) {
    throw new Error(
      "No Ethereum wallet found. Install MetaMask (or another injected wallet) to submit transactions.",
    );
  }
  return createClient({
    chain: studionet,
    account: account as `0x${string}`,
    provider: provider as unknown as never,
  });
}

/** Ask the wallet to switch / add the StudioNet chain. */
export async function connectNetwork(client: GenLayerClient): Promise<void> {
  await (client as any).connect(GENLAYER_NETWORK);
}

// ---- generic view call --------------------------------------------------

function isTransientRpc(e: unknown): boolean {
  const s = String((e as Error)?.message ?? e).toLowerCase();
  return (
    s.includes("failed to fetch") ||
    s.includes("fetch failed") ||
    s.includes("network") ||
    s.includes("timeout") ||
    s.includes("429") ||
    s.includes("502") ||
    s.includes("503") ||
    s.includes("unknown rpc error")
  );
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function view<T>(
  functionName: string,
  args: unknown[] = [],
): Promise<T> {
  const c = readClient() as any;
  let lastErr: unknown;
  for (let attempt = 0; attempt < 5; attempt++) {
    try {
      return (await c.readContract({
        address: CONTRACT_ADDRESS,
        functionName,
        args,
      })) as T;
    } catch (e) {
      lastErr = e;
      if (!isTransientRpc(e)) throw e;
      await sleep(400 * (attempt + 1));
    }
  }
  throw lastErr;
}

/** A view that returns `undefined` instead of throwing on "not found". */
export async function viewOpt<T>(
  functionName: string,
  args: unknown[] = [],
): Promise<T | undefined> {
  try {
    return await view<T>(functionName, args);
  } catch (e) {
    const s = String((e as Error)?.message ?? e).toLowerCase();
    if (s.includes("not found")) return undefined;
    throw e;
  }
}

// ---- receipt inspection ------------------------------------------------

interface LeafResult {
  status?: string;
  payload?: unknown;
}

function deepFind<T>(
  root: unknown,
  pick: (o: Record<string, unknown>) => T | undefined,
): T | undefined {
  const seen = new Set<unknown>();
  const stack: unknown[] = [root];
  while (stack.length) {
    const node = stack.pop();
    if (!node || typeof node !== "object" || seen.has(node)) continue;
    seen.add(node);
    if (!Array.isArray(node)) {
      const hit = pick(node as Record<string, unknown>);
      if (hit !== undefined) return hit;
    }
    for (const v of Object.values(node as Record<string, unknown>)) {
      if (v && typeof v === "object") stack.push(v);
    }
  }
  return undefined;
}

function readablePayload(p: unknown): string {
  if (p == null) return "";
  if (typeof p === "string") return p;
  if (typeof p === "object" && "readable" in (p as Record<string, unknown>)) {
    return String((p as Record<string, unknown>).readable ?? "");
  }
  return String(p);
}

/**
 * Classify a genlayer-js transaction receipt.
 *  - { kind: "ok", returnValue }         : leader executed, committed
 *  - throws ContractRevertError          : leader reverted (UserError)
 *  - throws UndeterminedError            : no decisive consensus / no leader result
 */
export function classifyReceipt(receipt: unknown): { returnValue?: string } {
  // First decisive leaf result (status === "return" | "rollback").
  const leaf = deepFind<LeafResult>(receipt, (o) => {
    if (
      (o.status === "return" || o.status === "rollback") &&
      "payload" in o
    ) {
      return o as LeafResult;
    }
    return undefined;
  });

  const resultName = deepFind<string>(receipt, (o) =>
    typeof o.result_name === "string" ? (o.result_name as string) : undefined,
  );
  const statusName = deepFind<string>(receipt, (o) =>
    typeof o.status_name === "string" ? (o.status_name as string) : undefined,
  );

  const disagree =
    (resultName ?? "").toUpperCase().includes("DISAGREE") ||
    (resultName ?? "").toUpperCase().includes("UNDETERMINED") ||
    (statusName ?? "").toUpperCase().includes("UNDETERMINED");

  if (leaf?.status === "rollback") {
    const reason = readablePayload(leaf.payload) || "transaction reverted";
    // A rollback that the validators unanimously agreed on is a genuine
    // contract revert. If they disagreed, treat as Undetermined.
    if (disagree) throw new UndeterminedError();
    throw new ContractRevertError(reason);
  }

  if (leaf?.status === "return") {
    return { returnValue: readablePayload(leaf.payload) };
  }

  // No decisive leaf. If consensus explicitly failed -> Undetermined.
  if (disagree) throw new UndeterminedError();

  // No leaf, no disagreement signal: nondeterministic step that produced
  // nothing to commit (e.g. semantic Undetermined surfaced as a bare revert).
  throw new UndeterminedError(
    "The transaction did not commit a result (treated as Undetermined).",
  );
}

// ---- write call + receipt --------------------------------------------
export interface WriteResult {
  hash: string;
  returnValue?: string;
  receipt: unknown;
}

export async function writeAndWait(
  client: GenLayerClient,
  functionName: string,
  args: unknown[],
  valueWei = 0n,
): Promise<WriteResult> {
  const c = client as any;
  const hash: string = await c.writeContract({
    address: CONTRACT_ADDRESS,
    functionName,
    args,
    value: valueWei,
  });
  const receipt = await c.waitForTransactionReceipt({
    hash,
    status: TransactionStatus.ACCEPTED,
    interval: 4000,
    retries: 120,
  });
  const { returnValue } = classifyReceipt(receipt);
  return { hash, returnValue, receipt };
}

// hex string ("0x…") -> Uint8Array, for bytes-typed calldata args.
export function hexToBytes(hex: string): Uint8Array {
  let h = hex.startsWith("0x") ? hex.slice(2) : hex;
  if (h.length % 2 !== 0) h = "0" + h;
  const out = new Uint8Array(h.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(h.substr(i * 2, 2), 16);
  }
  return out;
}
