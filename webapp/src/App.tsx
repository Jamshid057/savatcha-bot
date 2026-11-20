import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import Cart from "./pages/Cart";
import Checkout from "./pages/Checkout";
import Home from "./pages/Home";
import { OrderDetailPage, OrdersPage } from "./pages/Orders";
import ProductPage from "./pages/Product";
import Profile from "./pages/Profile";
import Search from "./pages/Search";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Home />} />
        <Route path="search" element={<Search />} />
        <Route path="product/:id" element={<ProductPage />} />
        <Route path="cart" element={<Cart />} />
        <Route path="checkout" element={<Checkout />} />
        <Route path="orders" element={<OrdersPage />} />
        <Route path="orders/:id" element={<OrderDetailPage />} />
        <Route path="profile" element={<Profile />} />
      </Route>
    </Routes>
  );
}
