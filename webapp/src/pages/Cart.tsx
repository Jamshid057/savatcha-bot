import { useNavigate } from "react-router-dom";
import { useCart, useClearCart, useSetCartItem } from "../api/hooks";
import { Empty, ErrorState, MainAction, ProductImage, QuantityStepper, Skeleton } from "../components/ui";
import { nameOf, useT } from "../i18n";
import { formatPrice } from "../lib/format";

export default function CartPage() {
  const { t, lang } = useT();
  const navigate = useNavigate();
  const query = useCart();
  const setItem = useSetCartItem();
  const clear = useClearCart();

  if (query.isPending) return <Skeleton className="m-4 h-64" />;
  if (query.isError) return <ErrorState onRetry={() => void query.refetch()} />;
  const cart = query.data;
  if (cart.lines.length === 0) return <Empty icon="🛒" text={t("cart_empty")} />;

  return (
    <div className="space-y-3 p-4 pb-40">
      {cart.removed.length > 0 && (
        <div className="rounded-xl bg-danger/10 p-3 text-sm text-danger">
          {t("cart_removed", { names: cart.removed.map((p) => nameOf(p, lang)).join(", ") })}
        </div>
      )}
      {cart.lines.map((l) => (
        <div key={l.product.id} className="card flex items-center gap-3">
          <ProductImage
            src={l.product.image_url}
            alt={nameOf(l.product, lang)}
            className="h-16 w-16 shrink-0 rounded-xl"
          />
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium">{nameOf(l.product, lang)}</div>
            <div className="text-sm text-hint">{formatPrice(l.product.price, lang)}</div>
            <div className="mt-1 text-sm font-bold">{formatPrice(l.subtotal, lang)}</div>
          </div>
          <QuantityStepper
            value={l.quantity}
            onChange={(q) => setItem.mutate({ product: l.product, quantity: q })}
          />
        </div>
      ))}
      <div className="flex items-center justify-between px-1 text-lg font-bold">
        <span>{t("total")}</span>
        <span>{formatPrice(cart.total, lang)}</span>
      </div>
      <button className="btn-secondary w-full" onClick={() => clear.mutate()}>
        🗑 {t("clear_cart")}
      </button>
      <MainAction text={t("checkout_btn")} onClick={() => navigate("/checkout")} />
    </div>
  );
}
