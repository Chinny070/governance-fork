import { useCallback, useRef, useState } from "react";
import {
  ContractRevertError,
  UndeterminedError,
  type WriteResult,
} from "./genlayer";
import { readableError } from "./format";

export type TxPhase =
  | "idle"
  | "signing" // waiting for the wallet to sign
  | "mining" // waiting for the validator receipt
  | "reading" // re-reading authoritative state
  | "done"
  | "undetermined" // consensus not reached, zero state committed
  | "reverted" // contract UserError, zero state committed
  | "error"; // wallet / network / decode failure

export interface TxState {
  phase: TxPhase;
  hash: string | null;
  message: string | null;
  result: WriteResult | null;
}

const INITIAL: TxState = {
  phase: "idle",
  hash: null,
  message: null,
  result: null,
};

export interface RunOptions {
  /** Runs after the receipt is confirmed; use it to re-read state. */
  afterConfirm?: (r: WriteResult) => Promise<void> | void;
}

export function useTx() {
  const [state, setState] = useState<TxState>(INITIAL);
  const running = useRef(false);

  const reset = useCallback(() => setState(INITIAL), []);

  const run = useCallback(
    async (
      action: () => Promise<WriteResult>,
      opts: RunOptions = {},
    ): Promise<WriteResult | null> => {
      if (running.current) return null;
      running.current = true;
      setState({ ...INITIAL, phase: "signing", message: "Confirm in your wallet…" });
      try {
        // The action calls writeContract (signing) then waits for the
        // receipt (mining). We can't observe the boundary precisely, so we
        // flip to "mining" on the next tick.
        const p = action();
        setTimeout(() => {
          setState((s) =>
            s.phase === "signing"
              ? { ...s, phase: "mining", message: "Waiting for validators…" }
              : s,
          );
        }, 400);
        const result = await p;
        setState({
          phase: "reading",
          hash: result.hash,
          message: "Re-reading on-chain state…",
          result,
        });
        if (opts.afterConfirm) await opts.afterConfirm(result);
        setState({
          phase: "done",
          hash: result.hash,
          message: "Confirmed.",
          result,
        });
        return result;
      } catch (e) {
        if (e instanceof UndeterminedError) {
          setState({
            phase: "undetermined",
            hash: null,
            message:
              "Undetermined — the validators did not reach consensus. " +
              "No state changed. You can retry (re-arm and run again).",
            result: null,
          });
        } else if (e instanceof ContractRevertError) {
          setState({
            phase: "reverted",
            hash: null,
            message: `Rejected by the contract: ${e.reason}`,
            result: null,
          });
        } else {
          setState({
            phase: "error",
            hash: null,
            message: readableError(e),
            result: null,
          });
        }
        return null;
      } finally {
        running.current = false;
      }
    },
    [],
  );

  return { ...state, run, reset, busy: state.phase === "signing" || state.phase === "mining" || state.phase === "reading" };
}
