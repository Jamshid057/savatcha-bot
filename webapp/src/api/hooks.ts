import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";
import { withQuantity } from "../lib/cart";
import type { Lang } from "../lib/format";
import { useApp } from "../store/app";
import { api, ApiError } from "./client";
import type { Cart, Category, Order, Page, Product, User } from "./types";

export const qk = {
  me: ["me"] as const,
  categories: ["categories"] as const,
  products: (category: number | null, q: string) => ["products", category, q] as const,
  product: (id: number) => ["product", id] as const,
  cart: ["cart"] as const,
  orders: ["orders"] as const,
  order: (id: number) => ["order", id] as const,
};

export function errorText(err: unknown, t: (k: string) => string): string {
  if (err instanceof ApiError) {
    const key = `err_${err.detail}`;
    const text = t(key);
    if (text !== key) return text;
  }
  return t("err_generic");
}

export const useMe = () =>
  useQuery({ queryKey: qk.me, queryFn: () => api<User>("/me"), staleTime: 60_000, retry: false });

export const useCategories = () =>
  useQuery({ queryKey: qk.categories, queryFn: () => api<Category[]>("/categories") });

export function useProducts(category: number | null, q: string) {
  return useInfiniteQuery({
    queryKey: qk.products(category, q),
    initialPageParam: 1,
    queryFn: ({ pageParam }) =>
      api<Page<Product>>("/products", { query: { category, q, page: pageParam, per_page: 12 } }),
    getNextPageParam: (last) => (last.page < last.pages ? last.page + 1 : undefined),
  });
}

export const useProduct = (id: number) =>
  useQuery({ queryKey: qk.product(id), queryFn: () => api<Product>(`/products/${id}`) });

export const useCart = () =>
  useQuery({ queryKey: qk.cart, queryFn: () => api<Cart>("/cart") });

export function useSetCartItem() {
  const qc = useQueryClient();
  const showToast = useApp((s) => s.showToast);
  return useMutation({
    mutationKey: ["cart"],
    mutationFn: ({ product, quantity }: { product: Product; quantity: number }) =>
      api<Cart>(`/cart/items/${product.id}`, { method: "PUT", body: { quantity } }),
    onMutate: async ({ product, quantity }) => {
      await qc.cancelQueries({ queryKey: qk.cart });
      const prev = qc.getQueryData<Cart>(qk.cart);
      if (prev) qc.setQueryData(qk.cart, withQuantity(prev, product, quantity));
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(qk.cart, ctx.prev);
      showToast("!", "error");
    },
    onSuccess: (cart) => {
      // Tez ketma-ket bosishda eski javob yangisini bosib ketmasin
      if (qc.isMutating({ mutationKey: ["cart"] }) <= 1) qc.setQueryData(qk.cart, cart);
    },
  });
}

export function useClearCart() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<Cart>("/cart", { method: "DELETE" }),
    onSuccess: (cart) => qc.setQueryData(qk.cart, cart),
  });
}

export function useCreateOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (form: FormData) => api<Order>("/orders", { method: "POST", body: form }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.cart });
      void qc.invalidateQueries({ queryKey: qk.orders });
      void qc.invalidateQueries({ queryKey: qk.me });
    },
  });
}

export const useOrders = () =>
  useQuery({ queryKey: qk.orders, queryFn: () => api<Page<Order>>("/orders") });

export const useOrder = (id: number) =>
  useQuery({ queryKey: qk.order(id), queryFn: () => api<Order>(`/orders/${id}`) });

export function usePatchMe() {
  const qc = useQueryClient();
  const setLang = useApp((s) => s.setLang);
  return useMutation({
    mutationFn: (body: { lang?: Lang; phone?: string }) =>
      api<User>("/me", { method: "PATCH", body }),
    onSuccess: (user) => {
      qc.setQueryData(qk.me, user);
      if (user.lang) setLang(user.lang);
    },
  });
}

export function invalidateAll(qc: QueryClient): void {
  void qc.invalidateQueries();
}
