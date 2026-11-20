import { useNavigate } from "react-router-dom";
import { useCart, useCategories, useProducts, useSetCartItem } from "../api/hooks";
import type { Product } from "../api/types";
import { descOf, nameOf, useT } from "../i18n";
import { formatPrice } from "../lib/format";
import { haptic } from "../lib/telegram";
import { Empty, ErrorState, InfiniteSentinel, ProductGridSkeleton, ProductImage } from "./ui";

export function CategoryChips({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (id: number | null) => void;
}) {
  const { t, lang } = useT();
  const { data } = useCategories();
  const chip = (active: boolean) =>
    `shrink-0 rounded-full px-4 py-2 text-sm font-medium transition ${
      active ? "bg-accent text-accent-text" : "bg-surface text-text"
    }`;
  return (
    <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 [scrollbar-width:none]">
      <button className={chip(value === null)} onClick={() => onChange(null)}>
        {t("all")}
      </button>
      {data?.map((c) => (
        <button
          key={c.id}
          className={chip(value === c.id)}
          onClick={() => {
            haptic.select();
            onChange(c.id);
          }}
        >
          {nameOf(c, lang)}
        </button>
      ))}
    </div>
  );
}

export function ProductCard({ product }: { product: Product }) {
  const { t, lang } = useT();
  const navigate = useNavigate();
  const cart = useCart();
  const setItem = useSetCartItem();
  const inCart = cart.data?.lines.find((l) => l.product.id === product.id)?.quantity ?? 0;
  return (
    <div className="card flex flex-col gap-2 p-2">
      <button className="text-left" onClick={() => navigate(`/product/${product.id}`)}>
        <ProductImage
          src={product.image_url}
          alt={nameOf(product, lang)}
          className="aspect-square w-full rounded-xl"
        />
        <div className="mt-2 line-clamp-2 min-h-10 text-sm font-medium">{nameOf(product, lang)}</div>
        <div className="text-sm font-bold">{formatPrice(product.price, lang)}</div>
      </button>
      {product.is_available ? (
        <button
          className="btn py-2"
          onClick={() => {
            haptic.tap();
            setItem.mutate({ product, quantity: inCart + 1 });
          }}
        >
          {inCart > 0 ? `🛒 ${inCart}` : t("add_to_cart")}
        </button>
      ) : (
        <div className="rounded-xl bg-bg py-2 text-center text-xs text-hint">{t("out_of_stock")}</div>
      )}
    </div>
  );
}

export function ProductGrid({ category, q }: { category: number | null; q: string }) {
  const { t } = useT();
  const query = useProducts(category, q);
  if (query.isPending) return <ProductGridSkeleton />;
  if (query.isError) return <ErrorState onRetry={() => void query.refetch()} />;
  const items = query.data.pages.flatMap((p) => p.items);
  if (items.length === 0) return <Empty icon="🔍" text={t("nothing_found")} />;
  return (
    <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {items.map((p) => (
          <ProductCard key={p.id} product={p} />
        ))}
      </div>
      <InfiniteSentinel
        enabled={Boolean(query.hasNextPage) && !query.isFetchingNextPage}
        onVisible={() => void query.fetchNextPage()}
      />
      {query.isFetchingNextPage && <ProductGridSkeleton />}
    </>
  );
}

export { descOf };
