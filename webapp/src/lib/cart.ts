import type { Cart, CartLine, Product } from "../api/types";

export const MAX_QTY = 99;

export function cartCount(cart: Cart | undefined): number {
  return cart ? cart.lines.reduce((sum, l) => sum + l.quantity, 0) : 0;
}

/** Optimistik yangilash: miqdorni o'rnatadi (0 — o'chiradi), summani qayta hisoblaydi. */
export function withQuantity(cart: Cart, product: Product, quantity: number): Cart {
  const q = Math.min(Math.max(quantity, 0), MAX_QTY);
  const others = cart.lines.filter((l) => l.product.id !== product.id);
  const lines: CartLine[] =
    q === 0
      ? others
      : [...others, { product, quantity: q, subtotal: String(Number(product.price) * q) }];
  const ordered = [...lines].sort((a, b) => {
    const ia = cart.lines.findIndex((l) => l.product.id === a.product.id);
    const ib = cart.lines.findIndex((l) => l.product.id === b.product.id);
    return (ia === -1 ? Infinity : ia) - (ib === -1 ? Infinity : ib);
  });
  const total = ordered.reduce((s, l) => s + Number(l.subtotal), 0);
  return { ...cart, lines: ordered, total: String(total) };
}
