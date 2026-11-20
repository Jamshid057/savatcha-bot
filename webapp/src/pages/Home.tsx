import { useState } from "react";
import { ProductGrid, CategoryChips } from "../components/Catalog";

export default function Home() {
  const [category, setCategory] = useState<number | null>(null);
  return (
    <div className="space-y-4 p-4">
      <CategoryChips value={category} onChange={setCategory} />
      <ProductGrid category={category} q="" />
    </div>
  );
}
