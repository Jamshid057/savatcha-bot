import { Link, useParams, useSearchParams } from "react-router-dom";
import { useOrder, useOrders } from "../api/hooks";
import { Empty, ErrorState, Skeleton, StatusBadge, AuthedImage } from "../components/ui";
import { useT } from "../i18n";
import { formatDateTime, formatPrice } from "../lib/format";

export function OrdersPage() {
  const { t, lang } = useT();
  const query = useOrders();
  if (query.isPending) return <Skeleton className="m-4 h-48" />;
  if (query.isError) return <ErrorState onRetry={() => void query.refetch()} />;
  if (query.data.items.length === 0) return <Empty icon="📦" text={t("orders_empty")} />;
  return (
    <div className="space-y-3 p-4">
      <h1 className="text-xl font-bold">{t("tab_orders")}</h1>
      {query.data.items.map((o) => (
        <Link key={o.id} to={`/orders/${o.id}`} className="card block space-y-1">
          <div className="flex items-center justify-between">
            <span className="font-semibold">#{o.id}</span>
            <StatusBadge status={o.status} />
          </div>
          <div className="text-sm text-hint">{formatDateTime(o.created_at, lang)}</div>
          <div className="font-bold">{formatPrice(o.total, lang)}</div>
        </Link>
      ))}
    </div>
  );
}

export function OrderDetailPage() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const { t, lang } = useT();
  const query = useOrder(Number(id));
  if (query.isPending) return <Skeleton className="m-4 h-64" />;
  if (query.isError) return <ErrorState onRetry={() => void query.refetch()} />;
  const o = query.data;
  return (
    <div className="space-y-4 p-4 pb-24">
      {params.get("new") && (
        <div className="rounded-2xl bg-ok/15 p-4 text-center">
          <div className="text-4xl">🎉</div>
          <div className="mt-1 font-bold text-ok">{t("order_created", { id: o.id })}</div>
          <div className="text-sm text-hint">{t("order_created_hint")}</div>
        </div>
      )}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">#{o.id}</h1>
        <StatusBadge status={o.status} />
      </div>
      <div className="card space-y-1 text-sm">
        <div>👤 {o.customer_name}, {o.phone}</div>
        <div>📍 {o.address}</div>
        {o.comment && <div>💬 {o.comment}</div>}
        <div className="text-hint">{formatDateTime(o.created_at, lang)}</div>
      </div>
      <div className="card space-y-2">
        {o.items.map((i) => (
          <div key={i.product_id} className="flex justify-between text-sm">
            <span>{i.name} × {i.quantity}</span>
            <span className="font-medium">{formatPrice(i.subtotal, lang)}</span>
          </div>
        ))}
        <div className="flex justify-between border-t border-line pt-2 font-bold">
          <span>{t("total")}</span>
          <span>{formatPrice(o.total, lang)}</span>
        </div>
      </div>
      <div className="space-y-2">
        <h2 className="text-sm font-semibold uppercase text-hint">{t("history")}</h2>
        <ol className="space-y-1 border-l-2 border-line pl-3 text-sm">
          {o.history.map((h, i) => (
            <li key={i}>
              <span className="font-medium">{t(`status_${h.to_status}`)}</span>
              <span className="ml-2 text-hint">{formatDateTime(h.created_at, lang)}</span>
            </li>
          ))}
        </ol>
      </div>
      {o.has_receipt && (
        <AuthedImage path={`/orders/${o.id}/receipt`} alt={t("receipt")} className="max-h-72 rounded-xl" />
      )}
    </div>
  );
}
