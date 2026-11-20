import { describe, expect, it } from "vitest";
import { cartCount, withQuantity } from "./cart";
import { formatPrice, normalizePhone, parseServerDate } from "./format";
import type { Cart, Product } from "../api/types";
import { dictionaries } from "../i18n";

const product = (id: number, price: string): Product => ({
  id,
  category_id: 1,
  name_uz: `p${id}`,
  name_ru: `п${id}`,
  description_uz: "",
  description_ru: "",
  price,
  image_url: null,
  is_available: true,
  is_archived: false,
});

describe("formatPrice", () => {
  it("groups thousands and adds currency per language", () => {
    expect(formatPrice("12000.00", "uz")).toBe("12 000 so'm");
    expect(formatPrice(1250000, "ru")).toBe("1 250 000 сум");
    expect(formatPrice(0, "uz")).toBe("0 so'm");
  });
});

describe("normalizePhone", () => {
  it("accepts common Uzbek formats", () => {
    expect(normalizePhone("+998901234567")).toBe("+998901234567");
    expect(normalizePhone("998 90 123-45-67")).toBe("+998901234567");
    expect(normalizePhone("90 123 45 67")).toBe("+998901234567");
  });
  it("rejects invalid numbers", () => {
    expect(normalizePhone("+79001234567")).toBeNull();
    expect(normalizePhone("12345")).toBeNull();
    expect(normalizePhone("")).toBeNull();
  });
});

describe("parseServerDate", () => {
  it("treats naive timestamps as UTC and keeps explicit offsets", () => {
    expect(parseServerDate("2026-11-20T19:11:00").toISOString()).toBe("2026-11-20T19:11:00.000Z");
    expect(parseServerDate("2026-11-20T19:11:00Z").toISOString()).toBe("2026-11-20T19:11:00.000Z");
    expect(parseServerDate("2026-11-21T00:11:00+05:00").toISOString()).toBe("2026-11-20T19:11:00.000Z");
  });
});

describe("cart helpers", () => {
  const empty: Cart = { lines: [], total: "0", removed: [] };

  it("recalculates totals and keeps line order", () => {
    const a = product(1, "10000");
    const b = product(2, "2500.50");
    let cart = withQuantity(empty, a, 2);
    cart = withQuantity(cart, b, 1);
    cart = withQuantity(cart, a, 3);
    expect(cart.lines.map((l) => l.product.id)).toEqual([1, 2]);
    expect(Number(cart.total)).toBeCloseTo(32500.5);
    expect(cartCount(cart)).toBe(4);
  });

  it("removes a line at quantity 0 and clamps to 99", () => {
    const a = product(1, "100");
    expect(withQuantity(withQuantity(empty, a, 2), a, 0).lines).toHaveLength(0);
    expect(withQuantity(empty, a, 500).lines[0].quantity).toBe(99);
    expect(cartCount(undefined)).toBe(0);
  });
});

describe("i18n", () => {
  it("uz and ru have identical keys", () => {
    expect(Object.keys(dictionaries.ru).sort()).toEqual(Object.keys(dictionaries.uz).sort());
  });
});

describe("i18n usage", () => {
  it("every statically used key exists in both dictionaries", async () => {
    const { readdirSync, readFileSync, statSync } = await import("node:fs");
    const { join } = await import("node:path");
    const walk = (dir: string): string[] =>
      readdirSync(dir).flatMap((f) => {
        const p = join(dir, f);
        return statSync(p).isDirectory() ? walk(p) : /\.(ts|tsx)$/.test(f) && !f.endsWith(".test.ts") ? [p] : [];
      });
    const used = new Set<string>();
    for (const file of walk(join(__dirname, ".."))) {
      const src = readFileSync(file, "utf8");
      for (const m of src.matchAll(/\bt\(\s*"([a-z][a-z_0-9]*)"/g)) used.add(m[1]);
      for (const m of src.matchAll(/key: "((?:a|tab)_[a-z_0-9]*)"/g)) used.add(m[1]);
    }
    const missing = [...used].filter((k) => !(k in dictionaries.uz) || !(k in dictionaries.ru));
    expect(missing).toEqual([]);
  });
  it("dynamic status keys exist", () => {
    for (const s of ["new", "accepted", "delivering", "done", "cancelled"]) {
      expect(dictionaries.uz[`status_${s}`]).toBeTruthy();
    }
  });
});
