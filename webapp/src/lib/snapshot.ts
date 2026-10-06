// Import a real proposal from Snapshot by URL. Pure parsing/mapping helpers
// are separate from the network call so they can be unit-tested.

export interface SnapshotProposal {
  id: string;
  title: string;
  body: string;
  choices: string[];
  state: string;
  author: string;
  space: { id: string; name: string };
}

export interface ImportedFields {
  daoName: string;
  daoUrl: string;
  externalId: string;
  title: string;
  proposalUrl: string;
  keys: string[];
  values: string[];
}

/** Accepts snapshot.org/#/<space>/proposal/<id> and snapshot.box/#/s:<space>/proposal/<id>. */
export function parseSnapshotUrl(raw: string): { space: string; id: string } | null {
  const m = raw
    .trim()
    .match(
      /^https?:\/\/(?:www\.)?(?:snapshot\.org|snapshot\.box|testnet\.snapshot\.org)\/#\/(?:s:|[a-z]+:)?([^/\s]+)\/proposal\/(0x[0-9a-fA-F]{64})\/?$/,
    );
  if (!m) return null;
  return { space: m[1], id: m[2] };
}

const clip = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
const oneLine = (s: string) => s.replace(/[\r\n]+/g, " ").trim();

export function mapSnapshot(p: SnapshotProposal): ImportedFields {
  const keys: string[] = [];
  const values: string[] = [];
  const add = (k: string, v: string) => {
    if (keys.length >= 32) return;
    keys.push(clip(oneLine(k), 64));
    values.push(clip(oneLine(v), 256));
  };
  add("source", "snapshot");
  add("space", p.space.id);
  add("state", p.state);
  add("author", p.author);
  p.choices.slice(0, 20).forEach((c, i) => add(`choice_${i + 1}`, c));
  return {
    daoName: clip(oneLine(p.space.name || p.space.id), 128),
    daoUrl: `https://snapshot.org/#/${p.space.id}`,
    externalId: clip(p.id, 128),
    title: clip(oneLine(p.title), 256),
    proposalUrl: `https://snapshot.org/#/${p.space.id}/proposal/${p.id}`,
    keys,
    values,
  };
}

const HUB = "https://hub.snapshot.org/graphql";

export async function fetchSnapshotProposal(id: string): Promise<SnapshotProposal> {
  const query = `query($id:String!){proposal(id:$id){id title body choices state author space{id name}}}`;
  const r = await fetch(HUB, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query, variables: { id } }),
  });
  if (!r.ok) throw new Error(`Snapshot hub returned HTTP ${r.status}`);
  const j = await r.json();
  const p = j?.data?.proposal;
  if (!p) throw new Error("Snapshot has no proposal with that id.");
  return p as SnapshotProposal;
}
