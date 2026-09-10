import { describe, it, expect } from "vitest";
import {
  classifyReceipt,
  ContractRevertError,
  UndeterminedError,
  hexToBytes,
} from "./genlayer";

// Fixtures modelled on real StudioNet receipts from the contract's e2e
// (scratchpad sm_lock.txt = success, n_settle_early.txt = rollback).

const successReceipt = {
  hash: "0xabc",
  status: 7,
  result: 6,
  consensus_data: {
    leader_receipt: [
      {
        execution_result: "SUCCESS",
        mode: "leader",
        result: { status: "return", payload: { readable: "1" } },
      },
    ],
  },
  result_name: "MAJORITY_AGREE",
  status_name: "FINALIZED",
};

const rollbackReceipt = {
  hash: "0xdef",
  status: 7,
  consensus_data: {
    leader_receipt: [
      {
        execution_result: "ERROR",
        mode: "leader",
        result: { status: "rollback", payload: "target not finalized" },
      },
      {
        execution_result: "ERROR",
        mode: "validator",
        result: { status: "rollback", payload: "target not finalized" },
      },
    ],
  },
  result_name: "MAJORITY_AGREE",
  status_name: "FINALIZED",
};

const undeterminedReceipt = {
  hash: "0x999",
  status: 6,
  consensus_data: { leader_receipt: [] },
  result_name: "MAJORITY_DISAGREE",
  status_name: "UNDETERMINED",
};

const disagreeRollbackReceipt = {
  hash: "0x111",
  consensus_data: {
    leader_receipt: [
      {
        execution_result: "ERROR",
        result: { status: "rollback", payload: "adjudication output rejected" },
      },
    ],
  },
  result_name: "MAJORITY_DISAGREE",
  status_name: "UNDETERMINED",
};

describe("classifyReceipt", () => {
  it("returns the decoded value on a committed leader return", () => {
    expect(classifyReceipt(successReceipt)).toEqual({ returnValue: "1" });
  });

  it("throws ContractRevertError with the reason on a unanimous rollback", () => {
    try {
      classifyReceipt(rollbackReceipt);
      throw new Error("should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(ContractRevertError);
      expect((e as ContractRevertError).reason).toBe("target not finalized");
    }
  });

  it("throws UndeterminedError when consensus failed and no leaf exists", () => {
    expect(() => classifyReceipt(undeterminedReceipt)).toThrow(UndeterminedError);
  });

  it("treats a rollback under MAJORITY_DISAGREE as Undetermined, not a revert", () => {
    expect(() => classifyReceipt(disagreeRollbackReceipt)).toThrow(
      UndeterminedError,
    );
  });

  it("throws UndeterminedError for an empty/garbage receipt", () => {
    expect(() => classifyReceipt({})).toThrow(UndeterminedError);
  });
});

describe("hexToBytes", () => {
  it("decodes an even-length 0x-prefixed hex string", () => {
    const b = hexToBytes("0x6d39");
    expect(Array.from(b)).toEqual([0x6d, 0x39]);
  });
  it("pads an odd-length string", () => {
    const b = hexToBytes("0xf");
    expect(Array.from(b)).toEqual([0x0f]);
  });
  it("handles the empty bytes marker", () => {
    expect(hexToBytes("0x").length).toBe(0);
  });
});
