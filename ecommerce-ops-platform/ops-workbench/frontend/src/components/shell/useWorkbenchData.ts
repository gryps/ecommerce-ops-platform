import { useCallback, useState } from "react";
import { api, storedToken } from "../../api";
import type {
  ClassifiedMaterial,
  CopyItem,
  JianyingDraft,
  MusicResource,
  Narration,
  Product,
  User,
} from "../../types";

export function useWorkbenchData() {
  const [user, setUser] = useState<User | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [materials, setMaterials] = useState<ClassifiedMaterial[]>([]);
  const [copies, setCopies] = useState<CopyItem[]>([]);
  const [narrations, setNarrations] = useState<Narration[]>([]);
  const [music, setMusic] = useState<MusicResource[]>([]);
  const [drafts, setDrafts] = useState<JianyingDraft[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [me, productRows, materialRows, copyRows, narrationRows, musicRows, draftRows] = await Promise.all([
        api<User>("/auth/me"),
        api<Product[]>("/products"),
        api<ClassifiedMaterial[]>("/human/classified-materials"),
        api<{ items: CopyItem[] }>("/human/copies/library?limit=200"),
        api<Narration[]>("/human/narrations"),
        api<MusicResource[]>("/music-resources"),
        api<JianyingDraft[]>("/human/jianying-drafts"),
      ]);
      setUser(me);
      setProducts(productRows);
      setMaterials(materialRows);
      setCopies(copyRows.items);
      setNarrations(narrationRows);
      setMusic(musicRows);
      setDrafts(draftRows);
    } catch (reason) {
      if (!storedToken()) setUser(null);
      else setError(reason instanceof Error ? reason.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  const act = async (work: () => Promise<unknown>, success: string) => {
    setError("");
    setNotice("");
    try {
      await work();
      setNotice(success);
      await refresh();
      return true;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "操作失败");
      return false;
    }
  };

  return {
    user,
    setUser,
    products,
    materials,
    copies,
    narrations,
    music,
    drafts,
    error,
    setError,
    notice,
    setNotice,
    loading,
    refresh,
    act,
  };
}
