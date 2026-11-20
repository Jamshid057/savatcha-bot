import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { errorText, useCart, useProduct, useSetCartItem } from "../api/hooks";
import { MainAction, ErrorState, ProductImage, QuantityStepper, Skeleton } from "../components/ui";
import { descOf, nameOf, useT } from "../i18n";
import { formatPrice } from "../lib/format";
import { haptic } from "../lib/telegram";
import { useApp } from "../store/app";

export default function ProductPage() {
  const { id } = useParams();
  const { t, lang } = useT();
  const navigate = useNavigate();
  const showToast = useApp((s) => s.showToast);
  const query = useProduct(Number(id));
  const cart = useCart();
  const setItem = useSetCartItem();
  const [qty, setQty] = useState(1);

  if (query.isPending) return <Skeleton className="m-4 h-96" />;
  if (query.isError) return <ErrorState onRetry={() => void query.refetch()} />;
  const p = query.data;
  const inCart = cart.data?.lines.find((l) => l.product.id === p.id)?.quantity ?? 0;

  const add = () => {
    haptic.success();
    setItem.mutate(
      { product: p, quantity: inCart + qty },
      {
        onSuccess: () => showToast(t("added_to_cart", { qty })),
        onError: (e) => showToast(errorText(e, t), "error"),
      },
    );
  };

  return (
    <div className="pb-32">
      <ProductImage src={p.image_url} alt={nameOf(p, lang)} className="aspect-square w-full" />
      <div className="space-y-3 p-4">
        <h1 className="text-xl font-bold">{nameOf(p, lang)}</h1>
        <div className="text-2xl font-extrabold text-accent">{formatPrice(p.price, lang)}</div>
        {descOf(p, lang) && <p className="whitespace-pre-line text-hint">{descOf(p, lang)}</p>}
        {p.is_available ? (
          <div className="flex items-center gap-3">
            <QuantityStepper value={qty} onChange={setQty} min={1} />
            {inCart > 0 && <span className="text-sm text-hint">{t("in_cart", { qty: inCart })}</span>}
          </div>
        ) : (
          <div className="rounded-xl bg-surface p-3 text-center text-hint">{t("out_of_stock")}</div>
        )}
      </div>
      <MainAction
        text={t("add_to_cart_btn")}
        onClick={add}
        visible={p.is_available}
        loading={setItem.isPending}
      />
      <button className="sr-only" onClick={() => navigate(-1)}>
        {t("back")}
      </button>
    </div>
  );
}
