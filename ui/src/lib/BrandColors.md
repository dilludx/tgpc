# TGPC Brand Colors — Mandatory Guideline

Every screen, component, export, and new code must use ONLY these in-house colors.

## The Four Brand Colors

| Name       | Hex      | Usage                                        |
|------------|----------|----------------------------------------------|
| tgpc green | `#00cc66`| Primary actions, active states, sync, "TGPC" |
| tgpc red   | `#ef4444`| Destructive, inactive, "RPh", disclaimer     |
| tgpc grey  | `#9ca3af`| Secondary text, "Registry", meta, placeholders |
| tgpc blue  | `#2563eb`| Links, RPC numbers, monospace values         |

## Supporting Neutrals (allowed)

| Token      | Hex       | Usage                          |
|------------|-----------|--------------------------------|
| text       | `#111827` | Primary text                   |
| muted      | `#6b7280` | Labels, secondary text         |
| border     | `#e5e7eb` | Borders, dividers              |
| row        | `#f4f4f5` | Table/row background           |
| bg         | `#ffffff` | Page background                |
| greenDark  | `#00b359` | Hover/dark variant of green    |

## Rules (MANDATORY)

1. Never invent new hex values. All colors come from the table above.
2. Prefer the `TGPC` export in `colors.ts`: `import { TGPC } from '$lib/colors'`.
   - `TGPC.green`, `TGPC.red`, `TGPC.grey`, `TGPC.blue`
3. Do NOT use off-brand reds like `#dc2626`, off-brand greens like `#16a34a`, or
   ad-hoc greys. If you find one, replace it with the brand value.
4. Category colors (`CATEGORY_COLORS`) use brand-derived values (blue, green,
   text, red, greenDark, grey) for data visualization — still on-palette.
5. New files: reference these constants; no hardcoded hex in markup.
