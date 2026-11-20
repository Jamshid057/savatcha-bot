import { useEffect, useState } from "react";
import { CategoryChips, ProductGrid } from "../components/Catalog";
import { useT } from "../i18n";

export function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

export default function Search() {
  const { t } = useT();
  const [text, setText] = useState("");
  const [category, setCategory] = useState<number | null>(null);
  const q = useDebounced(text.trim(), 300);
  return (
    <div className="space-y-4 p-4">
      <input
        className="input"
        type="search"
        placeholder={t("search_placeholder")}
        value={text}
        onChange={(e) => setText(e.target.value)}
        maxLength={50}
      />
      <CategoryChips value={category} onChange={setCategory} />
      <ProductGrid category={category} q={q} />
    </div>
  );
}
