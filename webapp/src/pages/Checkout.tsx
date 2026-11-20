import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { errorText, useCart, useCreateOrder, useMe } from "../api/hooks";
import { MainAction, Skeleton } from "../components/ui";
import { useT } from "../i18n";
import { formatPrice, normalizePhone } from "../lib/format";
import { haptic } from "../lib/telegram";
import { useApp } from "../store/app";

const MAX_RECEIPT_BYTES = 5 * 1024 * 1024;

export default function Checkout() {
  const { t, lang } = useT();
  const navigate = useNavigate();
  const showToast = useApp((s) => s.showToast);
  const me = useMe();
  const cart = useCart();
  const create = useCreateOrder();

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [comment, setComment] = useState("");
  const [receipt, setReceipt] = useState<File | null>(null);
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (me.data) {
      setName((n) => n || me.data.full_name);
      setPhone((p) => p || me.data.phone || "");
    }
  }, [me.data]);

  const preview = useMemo(() => (receipt ? URL.createObjectURL(receipt) : null), [receipt]);
  useEffect(() => () => (preview ? URL.revokeObjectURL(preview) : undefined), [preview]);

  const errors = {
    name: name.trim().length < 2,
    phone: normalizePhone(phone) === null,
    address: address.trim().length < 5,
    receipt: !receipt,
  };
  const valid = !Object.values(errors).some(Boolean);

  const submit = () => {
    setTouched(true);
    if (!valid || !receipt) {
      haptic.error();
      return;
    }
    const form = new FormData();
    form.set("customer_name", name.trim());
    form.set("phone", normalizePhone(phone) ?? phone);
    form.set("address", address.trim());
    form.set("comment", comment.trim());
    form.set("receipt", receipt);
    create.mutate(form, {
      onSuccess: (order) => {
        haptic.success();
        navigate(`/orders/${order.id}?new=1`, { replace: true });
      },
      onError: (e) => {
        haptic.error();
        showToast(errorText(e, t), "error");
      },
    });
  };

  if (cart.isPending) return <Skeleton className="m-4 h-64" />;
  const field = (bad: boolean) => (touched && bad ? "border-danger" : "");

  return (
    <div className="space-y-4 p-4 pb-40">
      <h1 className="text-xl font-bold">{t("checkout_title")}</h1>
      <label className="block space-y-1">
        <span className="text-sm text-hint">{t("field_name")}</span>
        <input className={`input ${field(errors.name)}`} value={name} onChange={(e) => setName(e.target.value)} maxLength={100} />
      </label>
      <label className="block space-y-1">
        <span className="text-sm text-hint">{t("field_phone")}</span>
        <input
          className={`input ${field(errors.phone)}`}
          type="tel"
          inputMode="tel"
          placeholder="+998 90 123 45 67"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        {touched && errors.phone && <span className="text-xs text-danger">{t("err_invalid_phone")}</span>}
      </label>
      <label className="block space-y-1">
        <span className="text-sm text-hint">{t("field_address")}</span>
        <textarea className={`input ${field(errors.address)}`} rows={2} value={address} onChange={(e) => setAddress(e.target.value)} maxLength={300} />
      </label>
      <label className="block space-y-1">
        <span className="text-sm text-hint">{t("field_comment")}</span>
        <textarea className="input" rows={2} value={comment} onChange={(e) => setComment(e.target.value)} maxLength={500} />
      </label>
      <div className="space-y-2">
        <span className="text-sm text-hint">{t("field_receipt")}</span>
        <label className={`btn-secondary w-full cursor-pointer ${field(errors.receipt)} border border-transparent`}>
          📷 {receipt ? t("receipt_change") : t("receipt_choose")}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null;
              if (f && f.size > MAX_RECEIPT_BYTES) {
                showToast(t("err_image_too_large"), "error");
                return;
              }
              setReceipt(f);
            }}
          />
        </label>
        {touched && errors.receipt && <span className="text-xs text-danger">{t("err_receipt_required")}</span>}
        {preview && <img src={preview} alt="" className="max-h-48 rounded-xl" />}
      </div>
      <div className="flex items-center justify-between text-lg font-bold">
        <span>{t("total")}</span>
        <span>{formatPrice(cart.data?.total ?? 0, lang)}</span>
      </div>
      <MainAction text={t("confirm_order")} onClick={submit} loading={create.isPending} />
    </div>
  );
}
