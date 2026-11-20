from savatcha.core.db.models import Order
from savatcha.core.i18n import t
from savatcha.core.utils.money import format_price

SOURCE_LABEL = {"classic": "🤖 Classic", "miniapp": "📱 Mini App"}


def status_label(status: str, lang: str | None) -> str:
    return t(f"status_{status}", lang)


def format_order_text(order: Order, lang: str | None, *, admin: bool = False) -> str:
    """Buyurtmaning matn ko'rinishi (order.items yuklangan bo'lishi kerak)."""
    lines = [t("order_title", lang, id=order.id, status=status_label(order.status, lang))]
    lines.append(t("order_date", lang, date=order.created_at.strftime("%d.%m.%Y %H:%M")))
    if admin:
        lines.append(t("order_source", lang, source=SOURCE_LABEL.get(order.source, order.source)))
    lines.append(t("order_customer", lang, name=order.customer_name, phone=order.phone))
    lines.append(t("order_address", lang, address=order.address))
    if order.comment:
        lines.append(t("order_comment", lang, comment=order.comment))
    lines.append("")
    for item in order.items:
        subtotal = format_price(item.price_snapshot * item.quantity, lang)
        lines.append(f"• {item.name_snapshot} × {item.quantity} = {subtotal}")
    lines.append("")
    lines.append(t("order_total", lang, total=format_price(order.total, lang)))
    if order.receipt_path:
        lines.append(t("order_has_receipt", lang))
    return "\n".join(lines)
