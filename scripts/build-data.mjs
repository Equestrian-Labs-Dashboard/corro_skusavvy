import fs from 'node:fs/promises';
import path from 'node:path';

const env = process.env;
const STORE = must(env.SHOPIFY_STORE, 'SHOPIFY_STORE');
const TOKEN = must(env.SHOPIFY_TOKEN, 'SHOPIFY_TOKEN');
const API_VERSION = env.SHOPIFY_API_VERSION || '2024-01';
const ATLETIX_KEYWORD = (env.ATLETIX_KEYWORD || 'atletix').toLowerCase();
const UNIT_COGS = Number(env.ATLETIX_UNIT_COGS || 89);
const INITIAL_STOCK = Number(env.ATLETIX_INITIAL_STOCK || 100);
const STOCK_RECEIVED_DATE = env.ATLETIX_STOCK_RECEIVED_DATE || '2025-12-26';
const SKU = env.ATLETIX_SKU || 'ATLETIX60';
const LOCATION_NAME = env.ATLETIX_LOCATION_NAME || 'New Wellington Warehouse';

const MARKETING_TERMS = [
  'marketing','sponsorship','sponsored','seeded','seeding','product seeding',
  'gift','elite gift','giveaway','promo','promotion','influencer','ambassador',
  'review','sample','press','pr','social','content creator'
];

const MANUAL_DEFAULTS = [
  {
    manual_id: 'MANUAL-MIRKO-H1-2026',
    period_hint: 'H1 2026',
    order_id: 'MANUAL-MIRKO-H1-2026',
    order_date: '2026-06-30T12:00:00Z',
    customer: 'Mirko Midili',
    customer_email: '',
    product: 'Atletix Horse',
    variant: '60 Doses',
    sku: SKU,
    quantity: 4,
    net: 0,
    unit_cogs: UNIT_COGS,
    cogs: round2(4 * UNIT_COGS),
    type: 'Atletix Request',
    reason: 'Manual Atletix shipment not found in Shopify',
    manual_shipping: 17.33,
    note: 'MIRKO MIDILI | 4412 Las Colinas Ln, Norman, OK 73072 | Phone: +1 580 559 6577',
    is_manual: true
  }
];

const PRESET_REQUESTS = [
  {
    match_order: '152336',
    match_customer: 'Sebastian Petroll',
    shipping: 70.26,
    reason: 'Atletix-paid shipping confirmed manually'
  }
];

function must(v, name) {
  if (!v) throw new Error(`Missing required secret: ${name}`);
  return v;
}
function round2(n) { return Math.round(Number(n || 0) * 100) / 100; }
function loose(s) { return String(s || '').trim().toLowerCase().replace(/\s+/g,' '); }
function hasAtletix(item) { return loose(`${item.title || ''} ${item.name || ''}`).includes(ATLETIX_KEYWORD); }
function hasMarketingMarker(order, item) {
  const chunks = [];
  chunks.push(order.tags || '', order.note || '');
  if (order.customer) chunks.push(order.customer.tags || '');
  for (const a of order.note_attributes || []) chunks.push(a.name || a.key || '', a.value || '');
  for (const p of item.properties || []) chunks.push(p.name || p.key || '', p.value || '');
  chunks.push(item.title || '', item.name || '');
  const text = loose(chunks.join(' '));
  for (const term of MARKETING_TERMS) {
    if (text.includes(loose(term))) return `Marketing marker: ${term}`;
  }
  return '';
}
function getOrderShipping(order) {
  const setAmt = order?.total_shipping_price_set?.shop_money?.amount;
  if (setAmt !== undefined && setAmt !== null && setAmt !== '') return round2(setAmt);
  if (order.total_shipping_price !== undefined && order.total_shipping_price !== null && order.total_shipping_price !== '') return round2(order.total_shipping_price);
  return round2((order.shipping_lines || []).reduce((s, l) => s + Number(l.price || 0), 0));
}
function customerName(order) {
  const c = order.customer;
  if (!c) return 'N/A';
  const name = `${c.first_name || ''} ${c.last_name || ''}`.trim();
  return name || 'N/A';
}
function customerEmail(order) {
  return order.email || order.contact_email || order.customer?.email || '';
}
function presetFor(row) {
  const oid = String(row.order_id || '').replace(/^#/, '');
  const customer = loose(row.customer);
  return PRESET_REQUESTS.find(p => String(p.match_order || '').replace(/^#/, '') === oid || customer.includes(loose(p.match_customer || '')));
}
async function shopFetch(url) {
  const resp = await fetch(url, { headers: { 'X-Shopify-Access-Token': TOKEN } });
  const text = await resp.text();
  if (!resp.ok) throw new Error(`Shopify API ${resp.status}: ${text.slice(0, 500)}`);
  return { json: JSON.parse(text), headers: resp.headers };
}
function buildShopUrl(pathname, params) {
  const qs = new URLSearchParams(params);
  return `https://${STORE}/admin/api/${API_VERSION}${pathname}?${qs.toString()}`;
}
async function fetchAllOrders() {
  const now = new Date();
  let start = new Date(`${STOCK_RECEIVED_DATE}T00:00:00Z`);
  if (Number.isNaN(start.getTime())) start = new Date(Date.UTC(now.getUTCFullYear(), 0, 1));
  const fields = 'id,name,email,contact_email,tags,created_at,line_items,customer,note,note_attributes,financial_status,cancelled_at,total_shipping_price_set,total_shipping_price,shipping_lines';
  let url = buildShopUrl('/orders.json', {
    status: 'any',
    created_at_min: start.toISOString(),
    created_at_max: now.toISOString(),
    limit: '250',
    fields
  });
  const out = [];
  while (url) {
    const { json, headers } = await shopFetch(url);
    out.push(...(json.orders || []));
    const link = headers.get('link') || '';
    const m = link.match(/<([^>]+)>;\s*rel="next"/);
    url = m ? m[1] : null;
  }
  return out;
}
function normalizeRows(orders) {
  const rows = [];
  for (const order of orders) {
    const orderShip = getOrderShipping(order);
    const cName = customerName(order);
    const cEmail = customerEmail(order);
    for (const item of order.line_items || []) {
      if (loose(item.title) === 'shipping') continue;
      if (!hasAtletix(item)) continue;
      const qty = parseInt(item.quantity || 0, 10);
      const gross = round2(Number(item.price || 0) * qty);
      const discount = round2((item.discount_allocations || []).reduce((s, d) => s + Number(d.amount || 0), 0));
      const net = round2(gross - discount);
      const unitCogs = UNIT_COGS;
      const cogs = round2(unitCogs * Math.max(qty, 0));
      const marketingReason = hasMarketingMarker(order, item);
      const isLikelyFree = gross > 0 && discount >= gross * 0.95;
      let type = 'Commercial';
      let reason = 'Paid Atletix sale';
      if (qty <= 0 || net < 0) {
        type = 'Credit / Return';
        reason = 'Negative quantity or net amount';
      } else if (marketingReason || net === 0 || isLikelyFree) {
        type = 'Marketing / Seeded';
        reason = marketingReason || (isLikelyFree ? '100% discount/free unit' : 'Net sales is zero');
      }
      const row = {
        order_id: order.name || String(order.id || ''),
        order_numeric_id: order.id || '',
        order_date: order.created_at || '',
        customer: cName,
        customer_email: cEmail,
        product: item.title || '',
        variant: item.variant_title || '',
        sku: item.sku || '',
        quantity: qty,
        gross, discount, net,
        unit_cogs: unitCogs,
        cogs,
        type,
        reason,
        category_source: reason,
        order_shipping_total: orderShip,
        manual_shipping: 0,
        note: '',
        is_manual: false
      };
      const preset = presetFor(row);
      if (preset) {
        row.type = 'Atletix Request';
        row.reason = preset.reason;
        row.category_source = 'Manual review selection';
        row.manual_shipping = preset.shipping;
        row.note = `${preset.match_customer || 'Atletix request'} shipping confirmed: $${preset.shipping}`;
      }
      rows.push(row);
    }
  }
  rows.sort((a,b) => new Date(b.order_date) - new Date(a.order_date));
  return rows;
}

const orders = await fetchAllOrders();
const rows = normalizeRows(orders);
const out = {
  generated_at: new Date().toISOString(),
  report_name: 'Atletix Horse Sales Report',
  source: 'GitHub Actions + Shopify Admin API',
  config: {
    keyword: ATLETIX_KEYWORD,
    unit_cogs: UNIT_COGS,
    initial_stock: INITIAL_STOCK,
    stock_received_date: STOCK_RECEIVED_DATE,
    sku: SKU,
    location_name: LOCATION_NAME
  },
  preset_requests: PRESET_REQUESTS,
  manual_defaults: MANUAL_DEFAULTS,
  rows
};
await fs.mkdir(path.resolve('data'), { recursive: true });
await fs.mkdir(path.resolve('public/data'), { recursive: true });
const json = JSON.stringify(out, null, 2);
await fs.writeFile(path.resolve('data/report.json'), json);
await fs.writeFile(path.resolve('public/data/report.json'), json);
console.log(`Generated data/report.json and public/data/report.json with ${rows.length} Atletix rows from ${orders.length} Shopify orders.`);
