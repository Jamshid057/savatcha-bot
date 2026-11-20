import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api, authHeaders, withQuery } from "./client";
import type { Category, Order, OrderStatus, Page, Product } from "./types";

export interface Period {
  from: string;
  to: string;
}

export interface Kpis {
  orders: number;
  revenue: number;
  avg_check: number;
  new_customers: number;
}
export interface Summary {
  period: { from: string; to: string; prev_from: string; prev_to: string };
  current: Kpis;
  previous: Kpis;
  change: Record<keyof Kpis, number | null>;
  pending: number;
}
export interface SalesDay {
  date: string;
  orders: number;
  revenue: number;
}
export interface TopProduct {
  product_id: number;
  name_uz: string;
  name_ru: string;
  quantity: number;
  revenue: number;
}
export interface SlowProduct {
  product_id: number;
  name_uz: string;
  name_ru: string;
  price: number;
}
export interface TopCustomers {
  customers: { user_id: number; full_name: string; username: string | null; orders: number; total_spent: number }[];
  buyers: number;
  repeat_buyers: number;
  repeat_share: number;
}
export interface Customer {
  id: number;
  tg_id: number;
  full_name: string;
  username: string | null;
  phone: string | null;
  lang: string | null;
  created_at: string;
  orders_count: number;
  total_spent: string;
  last_order_at: string | null;
}
export interface AuditItem {
  id: number;
  admin_tg_id: number;
  action: string;
  entity: string;
  entity_id: number | null;
  details: Record<string, unknown> | null;
  created_at: string;
}
export interface ShopSettings {
  shop_name: string;
  shop_phone: string;
  work_hours: string;
  notify_admin_ids: number[];
  admin_ids: number[];
}
export interface AdminSessionRow {
  id: number;
  created_at: string;
  expires_at: string;
  ip: string | null;
  user_agent: string | null;
  current: boolean;
}

export interface OrderFilters {
  status?: string;
  source?: string;
  from?: string;
  to?: string;
  q?: string;
  sort?: string;
  dir?: "asc" | "desc";
  page?: number;
  per_page?: number;
}

const stat = <T>(path: string, p: Period, extra: Record<string, string | number | boolean> = {}) =>
  api<T>(`/admin/stats/${path}`, { query: { ...p, ...extra } });

export const useStat = <T>(path: string, p: Period, extra: Record<string, string | number | boolean> = {}) =>
  useQuery({
    queryKey: ["stat", path, p.from, p.to, extra],
    queryFn: () => stat<T>(path, p, extra),
    placeholderData: keepPreviousData,
  });

export const useAdminOrders = (f: OrderFilters) =>
  useQuery({
    queryKey: ["admin", "orders", f],
    queryFn: () => api<Page<Order>>("/admin/orders", { query: { ...f } }),
    placeholderData: keepPreviousData,
  });

export function useChangeStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: OrderStatus }) =>
      api<Order>(`/admin/orders/${id}/status`, { method: "PATCH", body: { status } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["admin"] }),
  });
}

export function useBulkStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ids, status }: { ids: number[]; status: OrderStatus }) =>
      api<{ updated: number[]; failed: { id: number; reason: string }[] }>(
        "/admin/orders/bulk-status",
        { method: "PATCH", body: { ids, status } },
      ),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["admin"] }),
  });
}

export const useAdminCategories = () =>
  useQuery({ queryKey: ["admin", "categories"], queryFn: () => api<Category[]>("/admin/categories") });

export function useCategoryMutations() {
  const qc = useQueryClient();
  const done = () => void qc.invalidateQueries({ queryKey: ["admin", "categories"] });
  return {
    create: useMutation({
      mutationFn: (b: { name_uz: string; name_ru: string }) =>
        api<Category>("/admin/categories", { method: "POST", body: b }),
      onSuccess: done,
    }),
    update: useMutation({
      mutationFn: ({ id, ...b }: { id: number; name_uz?: string; name_ru?: string; is_active?: boolean }) =>
        api<Category>(`/admin/categories/${id}`, { method: "PATCH", body: b }),
      onSuccess: done,
    }),
    remove: useMutation({
      mutationFn: (id: number) => api<void>(`/admin/categories/${id}`, { method: "DELETE" }),
      onSuccess: done,
    }),
    reorder: useMutation({
      mutationFn: (ids: number[]) =>
        api<void>("/admin/categories/reorder", { method: "PATCH", body: { ids } }),
      onSuccess: done,
    }),
  };
}

export const useAdminProducts = (f: { category?: number; q?: string; page: number }) =>
  useQuery({
    queryKey: ["admin", "products", f],
    queryFn: () => api<Page<Product>>("/admin/products", { query: { ...f, per_page: 20 } }),
    placeholderData: keepPreviousData,
  });

export function useProductMutations() {
  const qc = useQueryClient();
  const done = () => void qc.invalidateQueries({ queryKey: ["admin", "products"] });
  return {
    save: useMutation({
      mutationFn: ({ id, form }: { id?: number; form: FormData }) =>
        api<Product>(id ? `/admin/products/${id}` : "/admin/products", {
          method: id ? "PATCH" : "POST",
          body: form,
        }),
      onSuccess: done,
    }),
    archive: useMutation({
      mutationFn: (ids: number[]) =>
        api<{ archived: number[] }>("/admin/products/bulk-archive", { method: "POST", body: { ids } }),
      onSuccess: done,
    }),
  };
}

export const useCustomers = (f: { search?: string; sort?: string; dir?: string; page: number }) =>
  useQuery({
    queryKey: ["admin", "customers", f],
    queryFn: () => api<Page<Customer>>("/admin/customers", { query: { ...f } }),
    placeholderData: keepPreviousData,
  });

export const useAudit = (f: { action?: string; from?: string; to?: string; page: number }) =>
  useQuery({
    queryKey: ["admin", "audit", f],
    queryFn: () => api<Page<AuditItem>>("/admin/audit", { query: { ...f } }),
    placeholderData: keepPreviousData,
  });

export const useShopSettings = () =>
  useQuery({ queryKey: ["admin", "settings"], queryFn: () => api<ShopSettings>("/admin/settings") });

export function useSaveSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (b: Partial<ShopSettings>) =>
      api<ShopSettings>("/admin/settings", { method: "PATCH", body: b }),
    onSuccess: (data) => qc.setQueryData(["admin", "settings"], data),
  });
}

export const useAdminSessions = () =>
  useQuery({ queryKey: ["admin", "sessions"], queryFn: () => api<AdminSessionRow[]>("/admin/sessions") });

/** CSV ni auth sarlavhasi/cookie bilan olib, faylga saqlaydi. */
export async function downloadCsv(path: string, query: Record<string, string | number | undefined>, filename: string) {
  const res = await fetch(withQuery(`/api${path}`, query), { headers: authHeaders(), credentials: "same-origin" });
  if (!res.ok) throw new Error(`http_${res.status}`);
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
