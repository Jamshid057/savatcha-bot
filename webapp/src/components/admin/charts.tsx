import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
  Legend,
} from "recharts";
import type { ReactNode } from "react";
import { useT } from "../../i18n";
import { formatPrice } from "../../lib/format";
import { shortDay } from "../../lib/dates";
import type { SalesDay } from "../../api/admin";

export const PALETTE = ["#3b82f6", "#10b981", "#f59e0b", "#a855f7", "#ef4444", "#14b8a6"];
const AXIS = { fontSize: 11, fill: "var(--c-hint)" };
const TOOLTIP = {
  contentStyle: {
    background: "var(--c-bg)",
    border: "1px solid var(--c-line)",
    borderRadius: 12,
    color: "var(--c-text)",
  },
};

function Box({ children, height = 240 }: { children: ReactNode; height?: number }) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        {children as React.ReactElement}
      </ResponsiveContainer>
    </div>
  );
}

export function SalesChart({ data }: { data: SalesDay[] }) {
  const { t, lang } = useT();
  return (
    <Box height={280}>
      <ComposedChart data={data}>
        <CartesianGrid stroke="var(--c-line)" vertical={false} />
        <XAxis dataKey="date" tickFormatter={shortDay} tick={AXIS} />
        <YAxis yAxisId="rev" tick={AXIS} tickFormatter={(v: number) => `${Math.round(v / 1000)}k`} width={44} />
        <YAxis yAxisId="ord" orientation="right" tick={AXIS} allowDecimals={false} width={28} />
        <Tooltip
          {...TOOLTIP}
          labelFormatter={(l: string) => l}
          formatter={(v: number, name: string) =>
            name === "revenue" ? [formatPrice(v, lang), t("a_revenue")] : [v, t("a_orders")]
          }
        />
        <Area yAxisId="rev" dataKey="revenue" stroke={PALETTE[0]} fill={PALETTE[0]} fillOpacity={0.18} type="monotone" />
        <Line yAxisId="ord" dataKey="orders" stroke={PALETTE[2]} strokeWidth={2} dot={false} type="monotone" />
      </ComposedChart>
    </Box>
  );
}

export function Donut({ data }: { data: { name: string; value: number }[] }) {
  const nonZero = data.filter((d) => d.value > 0);
  return (
    <Box>
      <PieChart>
        <Pie data={nonZero.length ? nonZero : [{ name: "—", value: 1 }]} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={2}>
          {(nonZero.length ? nonZero : [{ name: "—", value: 1 }]).map((_, i) => (
            <Cell key={i} fill={nonZero.length ? PALETTE[i % PALETTE.length] : "var(--c-line)"} />
          ))}
        </Pie>
        <Tooltip {...TOOLTIP} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </Box>
  );
}

export function HBars({ data, money = false }: { data: { name: string; value: number }[]; money?: boolean }) {
  const { lang } = useT();
  return (
    <Box>
      <BarChart data={data} layout="vertical" margin={{ left: 8 }}>
        <CartesianGrid stroke="var(--c-line)" horizontal={false} />
        <XAxis type="number" tick={AXIS} tickFormatter={(v: number) => (money ? `${Math.round(v / 1000)}k` : String(v))} />
        <YAxis type="category" dataKey="name" tick={AXIS} width={90} />
        <Tooltip {...TOOLTIP} formatter={(v: number) => (money ? formatPrice(v, lang) : v)} />
        <Bar dataKey="value" fill={PALETTE[0]} radius={[0, 6, 6, 0]} />
      </BarChart>
    </Box>
  );
}

export function VBars({ data, xKey, yKey, color = PALETTE[3] }: { data: object[]; xKey: string; yKey: string; color?: string }) {
  return (
    <Box>
      <BarChart data={data}>
        <CartesianGrid stroke="var(--c-line)" vertical={false} />
        <XAxis dataKey={xKey} tick={AXIS} interval={0} />
        <YAxis tick={AXIS} allowDecimals={false} width={28} />
        <Tooltip {...TOOLTIP} />
        <Bar dataKey={yKey} fill={color} radius={[6, 6, 0, 0]} />
      </BarChart>
    </Box>
  );
}

export function Lines({ data, xKey, yKey, color = PALETTE[1] }: { data: object[]; xKey: string; yKey: string; color?: string }) {
  return (
    <Box>
      <LineChart data={data}>
        <CartesianGrid stroke="var(--c-line)" vertical={false} />
        <XAxis dataKey={xKey} tick={AXIS} tickFormatter={shortDay} />
        <YAxis tick={AXIS} allowDecimals={false} width={28} />
        <Tooltip {...TOOLTIP} />
        <Line dataKey={yKey} stroke={color} strokeWidth={2} dot={false} type="monotone" />
      </LineChart>
    </Box>
  );
}
