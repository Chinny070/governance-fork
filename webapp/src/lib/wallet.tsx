import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { STUDIONET } from "./contract";
import {
  connectNetwork,
  getInjectedProvider,
  makeWriteClient,
  type GenLayerClient,
} from "./genlayer";
import { setActiveWriteClient } from "./activeClient";

interface WalletState {
  hasProvider: boolean;
  account: string | null;
  chainId: string | null;
  onStudionet: boolean;
  connecting: boolean;
  error: string | null;
  connect: () => Promise<void>;
  switchNetwork: () => Promise<void>;
  disconnect: () => void;
  /** Write client for the connected account, or null. */
  writeClient: GenLayerClient | null;
}

const Ctx = createContext<WalletState | null>(null);

function normChain(v: unknown): string | null {
  if (typeof v === "string") return v.toLowerCase();
  if (typeof v === "number") return "0x" + v.toString(16);
  return null;
}

export function WalletProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<string | null>(null);
  const [chainId, setChainId] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const provider = getInjectedProvider();
  const hasProvider = !!provider;
  const writeClientRef = useRef<{ acct: string; client: GenLayerClient } | null>(
    null,
  );

  const refreshChain = useCallback(async () => {
    if (!provider) return;
    try {
      const cid = await provider.request({ method: "eth_chainId" });
      setChainId(normChain(cid));
    } catch {
      /* ignore */
    }
  }, [provider]);

  // Passive: pick up an already-authorized account without prompting.
  useEffect(() => {
    if (!provider) return;
    let alive = true;
    (async () => {
      try {
        const accs = (await provider.request({
          method: "eth_accounts",
        })) as string[];
        if (alive && accs && accs.length) setAccount(accs[0]);
      } catch {
        /* ignore */
      }
      refreshChain();
    })();
    return () => {
      alive = false;
    };
  }, [provider, refreshChain]);

  // React to wallet events.
  useEffect(() => {
    if (!provider?.on) return;
    const onAccounts = (...a: unknown[]) => {
      const accs = a[0] as string[];
      setAccount(accs && accs.length ? accs[0] : null);
    };
    const onChain = (...a: unknown[]) => setChainId(normChain(a[0]));
    provider.on("accountsChanged", onAccounts);
    provider.on("chainChanged", onChain);
    return () => {
      provider.removeListener?.("accountsChanged", onAccounts);
      provider.removeListener?.("chainChanged", onChain);
    };
  }, [provider]);

  const connect = useCallback(async () => {
    setError(null);
    if (!provider) {
      setError(
        "No Ethereum wallet detected. Install MetaMask to submit transactions. Read-only exploration works without a wallet.",
      );
      return;
    }
    setConnecting(true);
    try {
      const accs = (await provider.request({
        method: "eth_requestAccounts",
      })) as string[];
      setAccount(accs?.[0] ?? null);
      await refreshChain();
    } catch (e) {
      setError((e as Error)?.message ?? "Wallet connection rejected.");
    } finally {
      setConnecting(false);
    }
  }, [provider, refreshChain]);

  const switchNetwork = useCallback(async () => {
    setError(null);
    if (!provider) return;
    try {
      // genlayer-js knows how to add + switch StudioNet.
      if (account) {
        await connectNetwork(makeWriteClient(account));
      } else {
        await provider.request({
          method: "wallet_switchEthereumChain",
          params: [{ chainId: STUDIONET.chainIdHex }],
        });
      }
      await refreshChain();
    } catch (e: any) {
      // 4902 = chain not added yet.
      if (e?.code === 4902 || String(e?.message).includes("Unrecognized chain")) {
        try {
          await provider.request({
            method: "wallet_addEthereumChain",
            params: [
              {
                chainId: STUDIONET.chainIdHex,
                chainName: STUDIONET.chainName,
                rpcUrls: [STUDIONET.rpcUrl],
                nativeCurrency: STUDIONET.nativeCurrency,
                blockExplorerUrls: [STUDIONET.explorerBase],
              },
            ],
          });
          await refreshChain();
        } catch (e2) {
          setError((e2 as Error)?.message ?? "Could not add StudioNet.");
        }
      } else {
        setError((e as Error)?.message ?? "Could not switch network.");
      }
    }
  }, [provider, account, refreshChain]);

  const disconnect = useCallback(() => {
    setAccount(null);
    writeClientRef.current = null;
  }, []);

  const onStudionet =
    chainId === STUDIONET.chainIdHex.toLowerCase() ||
    chainId === "0x" + STUDIONET.chainIdDec.toString(16);

  const writeClient = useMemo(() => {
    if (!account) {
      setActiveWriteClient(null);
      return null;
    }
    if (writeClientRef.current?.acct === account) {
      return writeClientRef.current.client;
    }
    try {
      const client = makeWriteClient(account);
      writeClientRef.current = { acct: account, client };
      setActiveWriteClient(client);
      return client;
    } catch {
      setActiveWriteClient(null);
      return null;
    }
  }, [account]);

  useEffect(() => {
    setActiveWriteClient(writeClient);
  }, [writeClient]);

  const value: WalletState = {
    hasProvider,
    account,
    chainId,
    onStudionet,
    connecting,
    error,
    connect,
    switchNetwork,
    disconnect,
    writeClient,
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useWallet(): WalletState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useWallet must be used within WalletProvider");
  return v;
}
