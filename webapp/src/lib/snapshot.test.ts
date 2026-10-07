import { describe, it, expect } from "vitest";
import { mapSnapshot, parseSnapshotUrl } from "./snapshot";

const ID = "0x" + "ab".repeat(32);
const ADDR = "0xf07DeD9dC292157749B6Fd268E37DF6EA38395B9";
const DEC = "104933844856336554027758452704713321330340501652892001249184191934279866979282";

describe("parseSnapshotUrl", () => {
  it("parses off-chain snapshot.org links", () => {
    expect(parseSnapshotUrl(`https://snapshot.org/#/arbitrumfoundation.eth/proposal/${ID}`)).toEqual({
      kind: "offchain",
      space: "arbitrumfoundation.eth",
      id: ID,
    });
  });
  it("parses off-chain snapshot.box links", () => {
    expect(parseSnapshotUrl(`https://snapshot.box/#/s:ens.eth/proposal/${ID}`)).toEqual({
      kind: "offchain",
      space: "ens.eth",
      id: ID,
    });
  });
  it("parses on-chain links, including the org/ prefix and a trailing-dot host", () => {
    const expected = { kind: "onchain", network: "arb1", space: ADDR, id: DEC };
    expect(parseSnapshotUrl(`https://snapshot.org./#/org/arbitrum/arb1:${ADDR}/proposal/${DEC}`)).toEqual(expected);
    expect(parseSnapshotUrl(`https://snapshot.box/#/arb1:${ADDR}/proposal/${DEC}`)).toEqual(expected);
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
      link: `https://snapshot.org/#/ens.eth/proposal/${ID}`,
      spaceLink: "https://snapshot.org/#/ens.eth",
    });
    expect(out.title.length).toBeLessThanOrEqual(256);
    expect(out.keys.length).toBe(out.values.length);
    expect(out.values.every((v) => v.length <= 256)).toBe(true);
    expect(out.keys).toContain("choice_1");
    expect(out.proposalUrl).toBe(`https://snapshot.org/#/ens.eth/proposal/${ID}`);
    expect(out.daoName).toBe("ENS");
    expect(out.daoUrl).toBe("https://snapshot.org/#/ens.eth");
  });
});
