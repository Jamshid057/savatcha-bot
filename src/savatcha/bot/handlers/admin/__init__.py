from savatcha.bot.handlers.admin import categories, orders, panel, products

routers = [panel.router, categories.router, products.router, orders.router]
