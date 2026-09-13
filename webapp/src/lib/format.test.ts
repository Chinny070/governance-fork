import { describe, it, expect } from "vitest";
import {
  formatGen,
  shortAddr,
  shortHex,
  isEmptyHex,
  sameAddr,
  readableError,
  isUndeterminedError,
} from "./format";

describe("formatGen", () => {
  it("formats whole GEN", () => {
    expect(formatGen(1_000_000_000_000_000_000n)).toBe("1 GEN");
  });
  it("formats the 0.1 GEN bond", () => {
    expect(formatGen(100_000_000_000_000_000n)).toBe("0.1 GEN");
  });
  it("formats the 0.05 GEN flip reward", () => {
    expect(formatGen(50_000_000_000_000_000n)).toBe("0.05 GEN");
  });
  it("trims trailing zeros and handles zero", () => {
    expect(formatGen(0n)).toBe("0 GEN");
    expect(formatGen(1_500_000_000_000_000_000n)).toBe("1.5 GEN");
  });
  it("accepts string and number", () => {
    expect(formatGen("100000000000000000")).toBe("0.1 GEN");
    expect(formatGen(0)).toBe("0 GEN");
  });
});

describe("address / hex helpers", () => {
  it("shortens addresses", () => {
    expect(shortAddr("0xD5A1E3b2087d439C36571B50947ddD900741f143")).toBe(
      "0xD5A1…f143",
    );
    expect(shortAddr(null)).toBe("—");
  });
  it("compares addresses case-insensitively", () => {
    expect(
      sameAddr(
        "0xBA06003F2C254232E4D440B89425ABC7AFD4C11A",
        "0xba06003f2c254232e4d440b89425abc7afd4c11a",
      ),
    ).toBe(true);
    expect(sameAddr(undefined, "0x1")).toBe(false);
  });
  it("recognises the empty bytes marker", () => {
    expect(isEmptyHex("0x")).toBe(true);
    expect(isEmptyHex("")).toBe(true);
    expect(isEmptyHex(null)).toBe(true);
    expect(isEmptyHex("0x6d39")).toBe(false);
  });
  it("shortens non-empty hex only", () => {
    expect(shortHex("0x")).toBe("—");
    expect(shortHex("0x" + "ab".repeat(32))).toMatch(/^0xababab…ababab$/);
  });
});

describe("error readers", () => {
  it("extracts a UserError message", () => {
    expect(readableError(new Error('gl.vm.UserError("bond already settled")'))).toBe(
      "bond already settled",
    );
  });
  it("passes through a plain string", () => {
    expect(readableError("wrong bond amount")).toBe("wrong bond amount");
  });
  it("detects Undetermined signatures", () => {
    expect(isUndeterminedError(new Error("Transaction is UNDETERMINED"))).toBe(
      true,
    );
    expect(
      isUndeterminedError(new Error("adjudication output rejected: bad schema")),
    ).toBe(true);
    expect(isUndeterminedError(new Error("root not found"))).toBe(false);
  });
});
