import { describe, it, expect } from "vitest";
import { mapSnapshot, parseSnapshotUrl } from "./snapshot";

const ID = "0x" + "ab".repeat(32);

describe("parseSnapshotUrl", () => {
  it("parses snapshot.org links", () => {
    expect(parseSnapshotUrl(`https://snapshot.org/#/arbitrumfoundation.eth/proposal/${ID}`)).toEqual({
      space: "arbitrumfoundation.eth",
      id: ID,
    });
  });
  it("parses snapshot.box links", () => {
    expect(parseSnapshotUrl(`https://snapshot.box/#/s:ens.eth/proposal/${ID}`)).toEqual({
      space: "ens.eth",
      id: ID,
    });
  });
  it("rejects other links", () => {
    expect(parseSnapshotUrl("https://example.com/x")).toBeNull();
    expect(parseSnapshotUrl("https://snapshot.org/#/ens.eth/proposal/notanid")).toBeNull();
  });
});

describe("mapSnapshot", () => {
  it("maps fields within contract length limits", () => {
    const out = mapSnapshot({
      id: ID,
      title: "T".repeat(400),
      body: "b",
      choices: ["For", "Against", "x".repeat(500)],
      state: "closed",
      author: "0xabc",
      space: { id: "ens.eth", name: "ENS" },
    });
    expect(out.title.length).toBeLessThanOrEqual(256);
    expect(out.keys.length).toBe(out.values.length);
    expect(out.values.every((v) => v.length <= 256)).toBe(true);
    expect(out.keys).toContain("choice_1");
    expect(out.proposalUrl).toBe(`https://snapshot.org/#/ens.eth/proposal/${ID}`);
    expect(out.daoName).toBe("ENS");
  });
});
