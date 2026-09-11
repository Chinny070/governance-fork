import { useEffect, useState } from "react";

export type Route =
  | { name: "explore" }
  | { name: "root"; id: bigint }
  | { name: "fork"; id: bigint }
  | { name: "build" }
  | { name: "bonds" }
  | { name: "about" };

function parse(hash: string): Route {
  const h = hash.replace(/^#\/?/, "");
  const [seg, arg] = h.split("/");
  switch (seg) {
    case "root":
      if (arg && /^\d+$/.test(arg)) return { name: "root", id: BigInt(arg) };
      return { name: "explore" };
    case "fork":
      if (arg && /^\d+$/.test(arg)) return { name: "fork", id: BigInt(arg) };
      return { name: "explore" };
    case "build":
      return { name: "build" };
    case "bonds":
      return { name: "bonds" };
    case "about":
      return { name: "about" };
    default:
      return { name: "explore" };
  }
}

export function toHash(r: Route): string {
  switch (r.name) {
    case "root":
      return `#/root/${r.id}`;
    case "fork":
      return `#/fork/${r.id}`;
    case "explore":
      return "#/";
    default:
      return `#/${r.name}`;
  }
}

export function navigate(r: Route) {
  const h = toHash(r);
  if (window.location.hash !== h) window.location.hash = h;
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parse(window.location.hash));
  useEffect(() => {
    const on = () => {
      setRoute(parse(window.location.hash));
      // This is a client-side hash router — the browser never resets scroll
      // on its own between "pages" the way a full navigation would.
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}
