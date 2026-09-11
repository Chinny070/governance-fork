import { describe, it, expect } from "vitest";
import { parseId } from "./api";
import {
  BOND_AMOUNT_WEI,
  CHALLENGE_GROUNDS_FORK,
  CHALLENGE_GROUNDS_ROOT_ENVELOPE,
  ENVELOPE_FINAL_STATUSES,
  FORK_FINAL_STATUSES,
} from "./enums";
import { toneFor } from "../components/ui";
import { flatten, type TreeNode } from "./tree";

describe("parseId", () => {
  it("parses a bare decimal return value", () => {
    expect(parseId("7", "lock_bond")).toBe(7n);
  });
  it("parses an id embedded in text", () => {
    expect(parseId("bond id = 12", "x")).toBe(12n);
  });
  it("throws on an empty return value", () => {
    expect(() => parseId(undefined, "create_fork")).toThrow(/create_fork/);
  });
});

describe("bond amount", () => {
  it("is 0.1 GEN in wei", () => {
    expect(BOND_AMOUNT_WEI).toBe(100_000_000_000_000_000n);
  });
});

describe("challenge grounds", () => {
  it("has 7 grounds per target kind, all distinct", () => {
    expect(new Set(CHALLENGE_GROUNDS_FORK).size).toBe(7);
    expect(new Set(CHALLENGE_GROUNDS_ROOT_ENVELOPE).size).toBe(7);
  });
  it("root-envelope grounds are namespaced where they collide with fork", () => {
    expect(CHALLENGE_GROUNDS_ROOT_ENVELOPE).toContain(
      "ENVELOPE_SOURCE_AUTHORITY_ERROR",
    );
    expect(CHALLENGE_GROUNDS_FORK).toContain("SOURCE_AUTHORITY_ERROR");
  });
});

describe("final status sets", () => {
  it("mark the terminal statuses", () => {
    expect(ENVELOPE_FINAL_STATUSES.has("ENVELOPE_FAITHFUL")).toBe(true);
    expect(ENVELOPE_FINAL_STATUSES.has("ENVELOPE_ADJUDICATING")).toBe(false);
    expect(FORK_FINAL_STATUSES.has("FINALIZED_NOT_FAITHFUL")).toBe(true);
    expect(FORK_FINAL_STATUSES.has("ADJUDICATING")).toBe(false);
  });
});

describe("toneFor", () => {
  it.each([
    ["ENVELOPE_FAITHFUL", "green"],
    ["FINALIZED_FAITHFUL", "green"],
    ["SUCCESS", "green"],
    ["FETCHED", "green"],
    ["SETTLED_FULL_REFUND", "green"],
    ["SETTLED_CHALLENGER_REWARD", "green"],
    ["RESOLVED_FLIPPED", "green"],
    ["ENVELOPE_REJECTED", "red"],
    ["NOT_FAITHFUL", "red"],
    ["FINALIZED_NOT_FAITHFUL", "red"],
    ["INVALID", "red"],
    ["FINALIZED_INVALID", "red"],
    ["ABORTED", "red"],
    ["FORK_CHALLENGE_OPEN", "coral"],
    ["ENVELOPE_CHALLENGE_OPEN", "coral"],
    ["OPEN", "coral"],
    ["UNUSABLE_SHORT", "coral"],
    ["SETTLED_PARTIAL_SLASH", "coral"],
    ["ENVELOPE_ADJUDICATING", "blue"],
    ["ADJUDICATING", "blue"],
    ["ENVELOPE_EVIDENCE_OPEN", "blue"],
    ["CASE_FROZEN", "blue"],
    ["UNSETTLED", "blue"],
    ["ENVELOPE_UNCLEAR", "neutral"],
    ["FINALIZED_UNCLEAR", "neutral"],
    ["RESOLVED_UNCHANGED", "neutral"],
    ["NOT_FETCHED", "neutral"],
    ["DRAFT", "neutral"],
  ])("classifies %s as %s", (value, tone) => {
    expect(toneFor(value)).toBe(tone);
  });
});

describe("flatten", () => {
  it("returns the node and all descendants depth-first", () => {
    const leaf = (id: bigint): TreeNode => ({
      kind: "fork",
      id,
      label: `#${id}`,
      status: "DRAFT",
      depth: 2,
      children: [],
    });
    const tree: TreeNode = {
      kind: "root",
      id: 1n,
      label: "root",
      status: "ENVELOPE_FAITHFUL",
      depth: 0,
      children: [
        { ...leaf(2n), children: [leaf(4n)] },
        leaf(3n),
      ],
    };
    expect(flatten(tree).map((n) => n.id)).toEqual([1n, 2n, 4n, 3n]);
  });
});
