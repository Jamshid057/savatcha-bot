import type { Lang } from "../lib/format";

export interface User {
  id: number;
  tg_id: number;
  full_name: string;
  username: string | null;
  lang: Lang | null;
  phone: string | null;
  is_admin: boolean;
}

export interface Category {
  id: number;
  name_uz: string;
  name_ru: string;
  sort_order: number;
  is_active: boolean;
}

export interface Product {
  id: number;
  category_id: number;
  name_uz: string;
  name_ru: string;
  description_uz: string;
  description_ru: string;
  price: string;
  image_url: string | null;
  is_available: boolean;
  is_archived: boolean;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  pages: number;
}

export interface CartLine {
  product: Product;
  quantity: number;
  subtotal: string;
}

export interface Cart {
  lines: CartLine[];
  total: string;
  removed: Product[];
}

export type OrderStatus = "new" | "accepted" | "delivering" | "done" | "cancelled";
export const ORDER_STATUSES: OrderStatus[] = ["new", "accepted", "delivering", "done", "cancelled"];
export const TRANSITIONS: Record<OrderStatus, OrderStatus[]> = {
  new: ["accepted", "cancelled"],
  accepted: ["delivering", "cancelled"],
  delivering: ["done", "cancelled"],
  done: [],
  cancelled: [],
};

export interface OrderItem {
  product_id: number;
  name: string;
  price: string;
  quantity: number;
  subtotal: string;
}

export interface OrderHistory {
  from_status: OrderStatus | null;
  to_status: OrderStatus;
  changed_by_tg_id: number | null;
  created_at: string;
}

export interface Order {
  id: number;
  source: "classic" | "miniapp";
  status: OrderStatus;
  customer_name: string;
  phone: string;
  address: string;
  comment: string | null;
  has_receipt: boolean;
  total: string;
  created_at: string;
  items: OrderItem[];
  history: OrderHistory[];
}
