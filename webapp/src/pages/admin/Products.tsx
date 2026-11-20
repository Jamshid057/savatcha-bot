import type { ColumnDef } from "@tanstack/react-table";
import { useEffect, useMemo, useState } from "react";
import { useAdminCategories, useAdminProducts, useProductMutations } from "../../api/admin";
import { errorText } from "../../api/hooks";
import type { Product } from "../../api/types";
import { Field, Modal, Pagination, ServerTable } from "../../components/admin/common";
import { ProductImage } from "../../components/ui";
import { nameOf, useT } from "../../i18n";

import { useApp } from "../../store/app";
import { useDebounced } from "../Search";

function PriceCell({ product, onSave }: { product: Product; onSave: (price: string) => void }) {
  const [value, setValue] = useState(String(Math.round(Number(product.price))));
  useEffect(() => setValue(String(Math.round(Number(product.price)))), [product.price]);
  const commit = () => {
    if (value.trim() && Number(value) > 0 && Number(value) !== Number(product.price)) onSave(value.trim());
    else setValue(String(Math.round(Number(product.price))));
  };
  return (
    <input
      className="input w-28 py-1.5"
      inputMode="numeric"
      value={value}
      aria-label="price"
      onChange={(e) => setValue(e.target.value.replace(/[^\d.]/g, ""))}
      onBlur={commit}
      onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
    />
  );
}

function ProductForm({ product, onClose }: { product: Product | null; onClose: () => void }) {
  const { t } = useT();
  const cats = useAdminCategories();
  const { save } = useProductMutations();
  const showToast = useApp((s) => s.showToast);
  const [f, setF] = useState({
    category_id: String(product?.category_id ?? ""),
    name_uz: product?.name_uz ?? "",
    name_ru: product?.name_ru ?? "",
    description_uz: product?.description_uz ?? "",
    description_ru: product?.description_ru ?? "",
    price: product ? String(Math.round(Number(product.price))) : "",
    is_available: product?.is_available ?? true,
  });
  const [image, setImage] = useState<File | null>(null);
  const preview = useMemo(() => (image ? URL.createObjectURL(image) : (product?.image_url ?? null)), [image, product]);
  useEffect(() => () => (image && preview ? URL.revokeObjectURL(preview) : undefined), [image, preview]);

  useEffect(() => {
    if (!f.category_id && cats.data?.[0]) setF((s) => ({ ...s, category_id: String(cats.data[0].id) }));
  }, [cats.data, f.category_id]);

  const submit = () => {
    const form = new FormData();
    for (const [k, v] of Object.entries(f)) form.set(k, String(v));
    if (image) form.set("image", image);
    save.mutate(
      { id: product?.id, form },
      {
        onSuccess: () => {
          showToast(t("saved"));
          onClose();
        },
        onError: (e) => showToast(errorText(e, t), "error"),
      },
    );
  };
  const valid = f.name_uz.trim() && f.name_ru.trim() && Number(f.price) > 0 && f.category_id;

  return (
    <Modal title={product ? t("a_edit_product") : t("a_add_product")} onClose={onClose}>
      <div className="space-y-3">
        <Field label={t("a_category")}>
          <select className="input" value={f.category_id} onChange={(e) => setF({ ...f, category_id: e.target.value })}>
            {cats.data?.map((c) => (
              <option key={c.id} value={c.id}>{c.name_uz} / {c.name_ru}</option>
            ))}
          </select>
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label={`${t("a_name")} (uz)`}><input className="input" value={f.name_uz} onChange={(e) => setF({ ...f, name_uz: e.target.value })} maxLength={200} /></Field>
          <Field label={`${t("a_name")} (ru)`}><input className="input" value={f.name_ru} onChange={(e) => setF({ ...f, name_ru: e.target.value })} maxLength={200} /></Field>
        </div>
        <Field label={`${t("a_description")} (uz)`}><textarea className="input" rows={2} value={f.description_uz} onChange={(e) => setF({ ...f, description_uz: e.target.value })} maxLength={1000} /></Field>
        <Field label={`${t("a_description")} (ru)`}><textarea className="input" rows={2} value={f.description_ru} onChange={(e) => setF({ ...f, description_ru: e.target.value })} maxLength={1000} /></Field>
        <Field label={t("a_price")}><input className="input" inputMode="numeric" value={f.price} onChange={(e) => setF({ ...f, price: e.target.value.replace(/[^\d.]/g, "") })} /></Field>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={f.is_available} onChange={(e) => setF({ ...f, is_available: e.target.checked })} />
          {t("a_available")}
        </label>
        <div className="space-y-2">
          <label className="btn-secondary cursor-pointer">
            🖼 {t("a_upload_image")}
            <input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(e) => setImage(e.target.files?.[0] ?? null)} />
          </label>
          {preview && <img src={preview} alt="" className="h-32 w-32 rounded-xl object-cover" />}
        </div>
        <button className="btn w-full" disabled={!valid || save.isPending} onClick={submit}>{t("save")}</button>
      </div>
    </Modal>
  );
}

export default function Products() {
  const { t, lang } = useT();
  const showToast = useApp((s) => s.showToast);
  const cats = useAdminCategories();
  const { save, archive } = useProductMutations();
  const [qText, setQText] = useState("");
  const q = useDebounced(qText.trim(), 300);
  const [category, setCategory] = useState<number | undefined>();
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [editing, setEditing] = useState<Product | null | "new">(null);
  const query = useAdminProducts({ category, q: q || undefined, page });
  const rows = query.data?.items ?? [];
  const catName = (id: number) => cats.data?.find((c) => c.id === id);

  const patch = (p: Product, fields: Record<string, string>) => {
    const form = new FormData();
    for (const [k, v] of Object.entries(fields)) form.set(k, v);
    save.mutate({ id: p.id, form }, { onSuccess: () => showToast(t("saved")), onError: (e) => showToast(errorText(e, t), "error") });
  };

  const columns = useMemo<ColumnDef<Product>[]>(
    () => [
      {
        id: "select",
        header: "",
        cell: ({ row }) => (
          <input
            type="checkbox"
            aria-label={`select ${row.original.id}`}
            checked={selected.has(row.original.id)}
            onChange={() => setSelected((s) => { const n = new Set(s); if (n.has(row.original.id)) n.delete(row.original.id); else n.add(row.original.id); return n; })}
            onClick={(e) => e.stopPropagation()}
          />
        ),
      },
      { id: "image", header: "", cell: ({ row }) => <ProductImage src={row.original.image_url} alt="" className="h-10 w-10 rounded-lg" /> },
      { id: "name", header: t("a_name"), cell: ({ row }) => <div><div className="font-medium">{nameOf(row.original, lang)}</div><div className="text-xs text-hint">{lang === "ru" ? row.original.name_uz : row.original.name_ru}</div></div> },
      { id: "category", header: t("a_category"), cell: ({ row }) => { const c = catName(row.original.category_id); return c ? nameOf(c, lang) : "—"; } },
      { id: "price", header: t("a_price"), cell: ({ row }) => <PriceCell product={row.original} onSave={(price) => patch(row.original, { price })} /> },
      {
        id: "available",
        header: t("a_available"),
        cell: ({ row }) => (
          <input type="checkbox" aria-label="available" checked={row.original.is_available} onChange={(e) => patch(row.original, { is_available: String(e.target.checked) })} />
        ),
      },
      { id: "actions", header: "", cell: ({ row }) => <button className="btn-secondary px-3 py-1.5" onClick={() => setEditing(row.original)}>✏️</button> },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [selected, lang, cats.data],
  );

  const bulkArchive = () =>
    archive.mutate([...selected], {
      onSuccess: () => { setSelected(new Set()); showToast(t("a_archived")); },
      onError: (e) => showToast(errorText(e, t), "error"),
    });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-extrabold">{t("a_nav_products")}</h1>
        <button className="btn" onClick={() => setEditing("new")}>➕ {t("a_add_product")}</button>
      </div>
      <div className="grid gap-2 sm:grid-cols-3">
        <input className="input" type="search" placeholder={t("search_placeholder")} value={qText} onChange={(e) => { setQText(e.target.value); setPage(1); }} />
        <select className="input" value={category ?? ""} onChange={(e) => { setCategory(e.target.value ? Number(e.target.value) : undefined); setPage(1); }}>
          <option value="">{t("a_all_categories")}</option>
          {cats.data?.map((c) => <option key={c.id} value={c.id}>{nameOf(c, lang)}</option>)}
        </select>
        {selected.size > 0 && <button className="btn-secondary" onClick={bulkArchive} disabled={archive.isPending}>🗑 {t("a_archive_selected", { n: selected.size })}</button>}
      </div>
      <ServerTable data={rows} columns={columns} loading={query.isFetching} />
      <Pagination page={page} pages={query.data?.pages ?? 1} total={query.data?.total ?? 0} onChange={setPage} />
      {editing && <ProductForm product={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

