const API = '/api';

const state = {
  token: localStorage.getItem('zaika_token') || null,
  user: JSON.parse(localStorage.getItem('zaika_user') || 'null'),
  view: 'browse',
  restaurants: [],
  selectedRestaurantId: null,
  selectedRestaurant: null,
  menuItems: [],
  cart: {},
  cartRestaurantId: null,
  orders: [],
  activeOrderId: null,
  activeOrder: null,
  trackingPoll: null,
  error: null,
  // restaurant-dashboard state
  restaurantView: 'my-restaurants',   // 'my-restaurants' | 'workspace'
  restaurantSubview: 'orders',        // 'orders' | 'menu' | 'earnings'
  myRestaurants: [],
  activeRestaurantId: null,
  activeRestaurant: null,
  restaurantMenuItems: [],
  restaurantOrders: [],
  // rider-dashboard state
  riderView: 'available',   // 'available' | 'my-deliveries' | 'earnings'
  availableOrders: [],
  myDeliveries: [],
  locationPingInterval: null,
  // admin-dashboard state
  adminView: 'pending',     // 'pending' | 'stats'
  pendingApprovals: [],
};

function saveAuth(token, user) {
  state.token = token;
  state.user = user;
  localStorage.setItem('zaika_token', token);
  localStorage.setItem('zaika_user', JSON.stringify(user));
}
function clearAuth() {
  state.token = null;
  state.user = null;
  localStorage.removeItem('zaika_token');
  localStorage.removeItem('zaika_user');
}
function cartCount() {
  return Object.values(state.cart).reduce((sum, c) => sum + c.quantity, 0);
}
function cartItemTotal() {
  return Object.values(state.cart).reduce((sum, c) => sum + c.item.price * c.quantity, 0);
}
function clearCart() {
  state.cart = {};
  state.cartRestaurantId = null;
}

async function api(method, path, body) {
  const headers = {'Content-Type': 'application/json'};
  if (state.token) headers['Authorization'] = 'Bearer ' + state.token;
  const res = await fetch(API + path, {
    method, headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  let data = {};
  try { data = await res.json(); } catch (err) { /* empty body */ }
  if (!res.ok) throw new Error(data.error || ('Request failed (' + res.status + ')'));
  return data;
}

function el(html) {
  const wrapper = document.createElement('div');
  wrapper.innerHTML = html.trim();
  return wrapper.firstElementChild;
}
function errorBox() {
  return state.error
    ? `<div class="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3 mb-4">${state.error}</div>`
    : '';
}
function money(n) {
  return '₹' + Number(n).toFixed(2);
}

function renderTrackingMap(containerId, points) {
  const el = document.getElementById(containerId);
  if (!el || typeof L === 'undefined') return;
  const pins = [
    points.restaurant && {...points.restaurant, color: '#E6532C', label: 'Restaurant'},
    points.delivery && {...points.delivery, color: '#2F8F4E', label: 'Delivery address'},
    points.rider && {...points.rider, color: '#F5A623', label: 'Delivery partner (live)'},
  ].filter(Boolean);
  if (!pins.length) { el.innerHTML = '<div class="text-xs text-gray-400 text-center py-8">No location data for this order yet.</div>'; return; }

  el.innerHTML = '';
  const map = L.map(containerId, {zoomControl: true, attributionControl: true}).setView([pins[0].lat, pins[0].lng], 14);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors', maxZoom: 19,
  }).addTo(map);

  const markers = pins.map(p =>
    L.circleMarker([p.lat, p.lng], {radius: 9, color: '#fff', weight: 2, fillColor: p.color, fillOpacity: 1})
      .addTo(map).bindPopup(p.label)
  );
  if (markers.length > 1) {
    map.fitBounds(L.featureGroup(markers).getBounds().pad(0.3));
  }
}

function render() {
  const root = document.getElementById('app');
  root.innerHTML = '';
  root.appendChild(state.token ? renderShell() : renderAuth());
}

// ================= Auth =================

function renderAuth() {
  const wrap = el(`
    <div class="min-h-screen flex items-center justify-center bg-[#FAF8F5] px-4">
      <div class="w-full max-w-sm">
        <div class="text-center mb-8">
          <div class="font-display text-4xl font-extrabold text-flame">Zaika</div>
          <div class="text-gray-500 mt-1 text-sm">Good food, delivered fast.</div>
        </div>
        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <div class="flex gap-2 mb-5">
            <button data-tab="login" class="tab-btn flex-1 py-2 rounded-xl font-semibold text-sm bg-flame text-white">Login</button>
            <button data-tab="register" class="tab-btn flex-1 py-2 rounded-xl font-semibold text-sm bg-gray-100 text-gray-500">Register</button>
          </div>
          ${errorBox()}
          <div id="auth-form"></div>
        </div>
      </div>
    </div>
  `);
  let activeTab = 'login';
  const formBox = wrap.querySelector('#auth-form');

  function loginHtml() {
    return `
      <div class="space-y-3">
        <input id="login-email" type="email" placeholder="Email" class="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm">
        <input id="login-password" type="password" placeholder="Password" class="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm">
        <button id="login-submit" class="w-full bg-flame text-white font-bold py-3 rounded-xl text-sm">Login</button>
      </div>`;
  }
  function registerHtml() {
    return `
      <div class="space-y-3">
        <input id="reg-name" placeholder="Full name" class="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm">
        <input id="reg-email" type="email" placeholder="Email" class="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm">
        <input id="reg-phone" placeholder="10-digit phone" class="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm">
        <input id="reg-password" type="password" placeholder="Password (min 8 chars)" class="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm">
        <select id="reg-role" class="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm">
          <option value="customer">Customer</option>
          <option value="restaurant">Restaurant owner</option>
          <option value="rider">Delivery rider</option>
        </select>
        <button id="register-submit" class="w-full bg-flame text-white font-bold py-3 rounded-xl text-sm">Create account</button>
      </div>`;
  }
  function paintForm() {
    formBox.innerHTML = activeTab === 'login' ? loginHtml() : registerHtml();
    if (activeTab === 'login') formBox.querySelector('#login-submit').addEventListener('click', onLogin);
    else formBox.querySelector('#register-submit').addEventListener('click', onRegister);
  }
  wrap.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      activeTab = btn.dataset.tab;
      wrap.querySelectorAll('.tab-btn').forEach(b => {
        b.className = 'tab-btn flex-1 py-2 rounded-xl font-semibold text-sm ' +
          (b.dataset.tab === activeTab ? 'bg-flame text-white' : 'bg-gray-100 text-gray-500');
      });
      paintForm();
    });
  });
  paintForm();
  return wrap;
}

async function onLogin() {
  const email = document.getElementById('login-email').value;
  const password = document.getElementById('login-password').value;
  try {
    const data = await api('POST', '/auth/login', {email, password});
    saveAuth(data.access_token, data.user);
    state.error = null;
    state.view = 'browse';
    render();
  } catch (e) { state.error = e.message; render(); }
}

async function onRegister() {
  const body = {
    full_name: document.getElementById('reg-name').value,
    email: document.getElementById('reg-email').value,
    phone: document.getElementById('reg-phone').value,
    password: document.getElementById('reg-password').value,
    role: document.getElementById('reg-role').value,
  };
  try {
    const data = await api('POST', '/auth/register', body);
    if (data.access_token) {
      saveAuth(data.access_token, data.user);
      state.error = null;
      state.view = 'browse';
      render();
    } else {
      state.error = null;
      window.alert(data.message);
      render();
    }
  } catch (e) { state.error = e.message; render(); }
}

// ================= Shell =================

function renderShell() {
  const isCustomer = state.user.role === 'customer';
  const wrap = el(`
    <div class="min-h-screen bg-[#FAF8F5] pb-10">
      <nav class="bg-white border-b border-gray-100 px-4 py-3 flex items-center justify-between sticky top-0 z-10">
        <div class="font-display text-xl font-extrabold text-flame">Zaika
          ${isCustomer ? '' : `<span class="text-xs font-semibold text-gray-400 ml-1 capitalize">${state.user.role}</span>`}
        </div>
        <div class="flex items-center gap-4 text-sm font-semibold text-gray-600">
          ${isCustomer ? `
            <button data-nav="browse" class="nav-btn">Browse</button>
            <button data-nav="cart" class="nav-btn">Cart${cartCount() ? ' (' + cartCount() + ')' : ''}</button>
            <button data-nav="orders" class="nav-btn">Orders</button>` : ''}
          <button id="notif-bell" class="relative text-lg">🔔<span id="notif-badge" class="absolute -top-1 -right-1 bg-flame text-white text-[10px] font-bold rounded-full w-4 h-4 items-center justify-center" style="display:none;"></span></button>
          <button id="logout-btn" class="text-gray-400 font-normal">Logout</button>
        </div>
      </nav>
      <main id="view" class="max-w-2xl mx-auto p-4"></main>
    </div>
  `);
  wrap.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => { state.view = btn.dataset.nav; state.error = null; render(); });
  });
  wrap.querySelector('#logout-btn').addEventListener('click', () => { clearAuth(); state.view = 'browse'; render(); });
  wrap.querySelector('#notif-bell').addEventListener('click', () => { state.view = 'notifications'; render(); });

  api('GET', '/notifications').then(data => { state.unreadCount = data.unread_count; updateNotifBadge(); }).catch(() => {});

  const viewBox = wrap.querySelector('#view');

  if (state.view === 'notifications') {
    viewBox.innerHTML = errorBox() + '<div id="notif-list" class="text-sm text-gray-400 text-center py-10">Loading...</div>';
    loadNotificationsList();
    return wrap;
  }

  if (state.user.role === 'restaurant') {
    renderRestaurantDashboard(viewBox);
    return wrap;
  }
  if (state.user.role === 'rider') {
    renderRiderDashboard(viewBox);
    return wrap;
  }
  if (state.user.role === 'admin') {
    renderAdminDashboard(viewBox);
    return wrap;
  }
  if (state.user.role !== 'customer') {
    viewBox.innerHTML = `
      <div class="bg-white rounded-2xl border border-gray-100 p-6 text-center">
        <div class="font-bold text-lg mb-1">Hi ${state.user.full_name} (${state.user.role})</div>
        <p class="text-sm text-gray-500">The ${state.user.role} web dashboard is a future milestone —
        every API for it is already live and tested.</p>
      </div>`;
    return wrap;
  }
  paintCurrentView(viewBox);
  return wrap;
}

function paintCurrentView(viewBox) {
  if (state.view === 'browse') {
    viewBox.innerHTML = `
      <div class="mb-3">
        <input id="search-input" placeholder="Search restaurants" class="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm mb-2">
        <div class="flex gap-2 flex-wrap">
          <select id="cuisine-filter" class="text-xs border border-gray-200 rounded-lg px-2 py-2 bg-white">
            <option value="">All cuisines</option>
            <option value="Biryani">Biryani</option>
            <option value="North Indian">North Indian</option>
            <option value="South Indian">South Indian</option>
            <option value="Maharashtrian">Maharashtrian</option>
            <option value="Chinese">Chinese</option>
            <option value="Street Food">Street Food</option>
            <option value="Desserts">Desserts</option>
          </select>
          <select id="rating-filter" class="text-xs border border-gray-200 rounded-lg px-2 py-2 bg-white">
            <option value="">Any rating</option>
            <option value="4">4+ ★</option>
            <option value="3">3+ ★</option>
          </select>
          <label class="flex items-center gap-1.5 text-xs border border-gray-200 rounded-lg px-3 py-2 bg-white">
            <input type="checkbox" id="veg-only-filter"> Veg only
          </label>
        </div>
      </div>
      ${errorBox()}
      <div id="restaurant-list" class="text-sm text-gray-400 text-center py-10">Loading...</div>
    `;
    const searchInput = document.getElementById('search-input');
    searchInput.addEventListener('keyup', (e) => { if (e.key === 'Enter') loadRestaurants(); });
    searchInput.addEventListener('blur', loadRestaurants);
    document.getElementById('cuisine-filter').addEventListener('change', loadRestaurants);
    document.getElementById('rating-filter').addEventListener('change', loadRestaurants);
    document.getElementById('veg-only-filter').addEventListener('change', loadRestaurants);
    loadRestaurants();
  } else if (state.view === 'menu') {
    viewBox.innerHTML = errorBox() + '<div id="menu-box" class="text-sm text-gray-400 text-center py-10">Loading...</div>';
    paintMenu();
  } else if (state.view === 'cart') {
    viewBox.innerHTML = errorBox() + '<div id="cart-box"></div>';
    paintCart();
  } else if (state.view === 'orders') {
    viewBox.innerHTML = errorBox() + '<div id="orders-list" class="text-sm text-gray-400 text-center py-10">Loading...</div>';
    loadOrders();
  } else if (state.view === 'order-detail') {
    viewBox.innerHTML = errorBox() + '<div id="order-detail-box" class="text-sm text-gray-400 text-center py-10">Loading...</div>';
    loadOrderDetail();
  }
}

// ================= Browse & Menu (customer) =================

async function loadRestaurants() {
  const params = new URLSearchParams();
  const search = document.getElementById('search-input')?.value.trim();
  const cuisine = document.getElementById('cuisine-filter')?.value;
  const rating = document.getElementById('rating-filter')?.value;
  const vegOnly = document.getElementById('veg-only-filter')?.checked;
  if (search) params.set('search', search);
  if (cuisine) params.set('cuisine', cuisine);
  if (rating) params.set('min_rating', rating);
  if (vegOnly) params.set('veg_only', 'true');

  try {
    const data = await api('GET', '/customer/restaurants?' + params.toString());
    state.restaurants = data.restaurants;
    state.error = null;
  } catch (e) { state.error = e.message; render(); return; }
  const box = document.getElementById('restaurant-list');
  if (!box) return;
  if (!state.restaurants.length) {
    box.innerHTML = '<p class="text-gray-400 text-sm text-center py-10">No restaurants match these filters.</p>';
    return;
  }
  box.innerHTML = state.restaurants.map(r => `
    <button data-id="${r.restaurant_id}" class="rest-card w-full text-left bg-white rounded-2xl border border-gray-100 p-4 mb-3 flex items-center justify-between">
      <div>
        <div class="font-bold">${r.name}</div>
        <div class="text-xs text-gray-500 mt-1">${r.cuisine_type || 'Restaurant'} · ${r.city}</div>
      </div>
      <div class="text-xs bg-amber-50 text-amber-700 font-bold px-2 py-1 rounded-lg">★ ${r.avg_rating || '—'}</div>
    </button>`).join('');
  box.querySelectorAll('.rest-card').forEach(btn => {
    btn.addEventListener('click', () => {
      state.selectedRestaurantId = parseInt(btn.dataset.id, 10);
      state.view = 'menu';
      render();
    });
  });
}

async function paintMenu() {
  try {
    const data = await api('GET', `/customer/restaurants/${state.selectedRestaurantId}/menu`);
    state.selectedRestaurant = data.restaurant;
    state.menuItems = data.menu_items;
    state.error = null;
  } catch (e) { state.error = e.message; render(); return; }
  const box = document.getElementById('menu-box');
  if (!box) return;
  const r = state.selectedRestaurant;
  box.innerHTML = `
    <button id="back-btn" class="text-sm text-gray-500 mb-3">&larr; Back to restaurants</button>
    <div class="mb-4">
      <div class="text-xl font-extrabold">${r.name}</div>
      <div class="text-xs text-gray-500">${r.cuisine_type || ''} · ${r.city}</div>
    </div>
    <div id="menu-items"></div>`;
  box.querySelector('#back-btn').addEventListener('click', () => { state.view = 'browse'; render(); });

  const itemsBox = box.querySelector('#menu-items');
  if (!state.menuItems.length) {
    itemsBox.innerHTML = '<p class="text-gray-400 text-sm text-center py-6">No menu items yet.</p>';
    return;
  }
  itemsBox.innerHTML = state.menuItems.map(item => `
    <div class="bg-white rounded-2xl border border-gray-100 p-4 mb-3 flex items-center gap-3">
      ${item.image_url ? `<img src="${item.image_url}" class="w-16 h-16 rounded-xl object-cover shrink-0">` : ''}
      <div class="flex-1 min-w-0">
        <div class="font-bold text-sm">${item.name}</div>
        <div class="text-sm mt-1">${money(item.price)}</div>
        ${item.description ? `<div class="text-xs text-gray-400 mt-1">${item.description}</div>` : ''}
      </div>
      <button data-id="${item.item_id}" class="add-btn border border-flame text-flame font-bold text-xs px-4 py-2 rounded-xl shrink-0">ADD</button>
    </div>`).join('');
  itemsBox.querySelectorAll('.add-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = state.menuItems.find(i => String(i.item_id) === btn.dataset.id);
      if (state.cartRestaurantId && state.cartRestaurantId !== state.selectedRestaurantId) {
        if (!window.confirm('Your cart has items from another restaurant. Clear it and add this instead?')) return;
        clearCart();
      }
      state.cartRestaurantId = state.selectedRestaurantId;
      const existing = state.cart[item.item_id];
      state.cart[item.item_id] = {item, quantity: existing ? existing.quantity + 1 : 1};
      render();
    });
  });

  const reviewsSection = document.createElement('div');
  reviewsSection.className = 'mt-4';
  reviewsSection.innerHTML = '<div class="text-xs font-bold text-gray-400 uppercase mb-2">Reviews</div><div id="reviews-list" class="text-xs text-gray-400">Loading...</div>';
  box.appendChild(reviewsSection);
  try {
    const rdata = await api('GET', `/customer/restaurants/${state.selectedRestaurantId}/reviews`);
    const rbox = reviewsSection.querySelector('#reviews-list');
    if (!rdata.reviews.length) {
      rbox.innerHTML = '<p class="text-gray-400">No reviews yet — be the first after your order arrives.</p>';
    } else {
      rbox.innerHTML = rdata.reviews.map(rv => `
        <div class="bg-white rounded-xl border border-gray-100 p-3 mb-2">
          <div class="flex items-center justify-between">
            <span class="font-semibold text-gray-700">${rv.customer_name || 'Customer'}</span>
            <span class="text-amber-500">${'★'.repeat(rv.food_rating)}${'☆'.repeat(5 - rv.food_rating)}</span>
          </div>
          ${rv.comment ? `<div class="text-gray-500 mt-1">${rv.comment}</div>` : ''}
        </div>`).join('');
    }
  } catch (e) { /* non-critical, fail quietly */ }
}

// ================= Cart / Checkout =================

function paintCart() {
  const box = document.getElementById('cart-box');
  if (!box) return;
  const items = Object.values(state.cart);
  if (!items.length) { box.innerHTML = '<p class="text-gray-400 text-sm text-center py-10">Your cart is empty.</p>'; return; }
  const itemTotal = cartItemTotal();
  const deliveryFee = 30;
  const taxes = Math.round(itemTotal * 0.05 * 100) / 100;
  const grand = Math.round((itemTotal + deliveryFee + taxes) * 100) / 100;

  box.innerHTML = `
    ${items.map(c => `
      <div class="bg-white rounded-2xl border border-gray-100 p-4 mb-3 flex items-center justify-between">
        <div><div class="font-bold text-sm">${c.item.name}</div><div class="text-xs text-gray-500">${money(c.item.price)} × ${c.quantity}</div></div>
        <div class="font-bold text-sm">${money(c.item.price * c.quantity)}</div>
      </div>`).join('')}
    <div class="bg-white rounded-2xl border border-gray-100 p-4 mb-3 text-sm space-y-1">
      <div class="flex justify-between text-gray-500"><span>Item total</span><span>${money(itemTotal)}</span></div>
      <div class="flex justify-between text-gray-500"><span>Delivery fee</span><span>${money(deliveryFee)}</span></div>
      <div class="flex justify-between text-gray-500"><span>Taxes</span><span>${money(taxes)}</span></div>
      <div class="flex justify-between font-bold text-base pt-2 border-t border-gray-100 mt-1"><span>Grand total</span><span>${money(grand)}</span></div>
    </div>
    <input id="delivery-address" placeholder="Delivery address" class="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm mb-2">
    <button id="use-location-btn" type="button" class="text-xs text-flame font-semibold mb-3">📍 Use my current location (for live tracking on the map)</button>
    <select id="payment-method" class="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm mb-3">
      <option value="cod">Cash on Delivery</option>
      <option value="upi">UPI</option>
      <option value="card">Card</option>
    </select>
    <button id="place-order-btn" class="w-full bg-flame text-white font-bold py-3 rounded-xl text-sm">Place Order · ${money(grand)}</button>
  `;
  box.querySelector('#place-order-btn').addEventListener('click', placeOrder);
  box.querySelector('#use-location-btn').addEventListener('click', (e) => {
    const btn = e.currentTarget;
    if (!navigator.geolocation) { state.error = 'Location not supported by this browser.'; render(); return; }
    btn.textContent = 'Getting location...';
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        state.checkoutLat = pos.coords.latitude;
        state.checkoutLng = pos.coords.longitude;
        btn.textContent = '✓ Location captured';
        btn.className = 'text-xs text-basil font-semibold mb-3';
      },
      () => { btn.textContent = '📍 Could not get location — try again'; },
    );
  });
}

async function placeOrder() {
  const address = document.getElementById('delivery-address').value.trim();
  const paymentMethod = document.getElementById('payment-method').value;
  if (!address) { state.error = 'Delivery address is required.'; render(); return; }
  const items = Object.values(state.cart).map(c => ({item_id: c.item.item_id, quantity: c.quantity}));
  try {
    const data = await api('POST', '/customer/orders', {
      restaurant_id: state.cartRestaurantId, items,
      delivery_address: address, payment_method: paymentMethod,
      delivery_latitude: state.checkoutLat, delivery_longitude: state.checkoutLng,
    });
    state.checkoutLat = null; state.checkoutLng = null;
    if (data.payment && data.payment.razorpay_order_id) {
      openRazorpayCheckout(data.order, data.payment);
    } else {
      clearCart();
      state.error = data.payment_error ? ('Order placed, but online payment setup failed: ' + data.payment_error + ' (you can still pay via COD next time)') : null;
      state.activeOrderId = data.order.order_id;
      state.view = 'order-detail';
      render();
    }
  } catch (e) { state.error = e.message; render(); }
}

function openRazorpayCheckout(order, payment) {
  const rzp = new Razorpay({
    key: payment.razorpay_key_id,
    amount: payment.amount,
    currency: payment.currency,
    order_id: payment.razorpay_order_id,
    name: 'Zaika',
    description: 'Order #' + order.order_id,
    theme: { color: '#E6532C' },
    handler: async function (response) {
      try {
        await api('POST', `/customer/orders/${order.order_id}/verify-payment`, {
          razorpay_order_id: response.razorpay_order_id,
          razorpay_payment_id: response.razorpay_payment_id,
          razorpay_signature: response.razorpay_signature,
        });
        clearCart();
        state.error = null;
      } catch (e) {
        state.error = 'Payment succeeded but verification failed: ' + e.message;
      }
      state.activeOrderId = order.order_id;
      state.view = 'order-detail';
      render();
    },
    modal: {
      ondismiss: function () {
        clearCart();
        state.error = 'Payment window closed. Your order is saved as unpaid — check Orders to retry.';
        state.activeOrderId = order.order_id;
        state.view = 'order-detail';
        render();
      }
    },
  });
  rzp.open();
}

// ================= Orders (customer) =================

async function loadOrders() {
  try {
    const data = await api('GET', '/customer/orders');
    state.orders = data.orders;
    state.error = null;
  } catch (e) { state.error = e.message; render(); return; }
  const box = document.getElementById('orders-list');
  if (!box) return;
  if (!state.orders.length) { box.innerHTML = '<p class="text-gray-400 text-sm text-center py-10">No orders yet.</p>'; return; }
  box.innerHTML = state.orders.map(o => `
    <button data-id="${o.order_id}" class="order-card w-full text-left bg-white rounded-2xl border border-gray-100 p-4 mb-3 flex items-center justify-between">
      <div>
        <div class="font-bold text-sm">${o.restaurant_name || ('Order #' + o.order_id)}</div>
        <div class="text-xs text-gray-500 mt-1">${new Date(o.placed_at).toLocaleString()}</div>
      </div>
      <div class="text-right">
        <div class="font-bold text-sm">${money(o.grand_total)}</div>
        <div class="text-xs mt-1 capitalize font-semibold ${o.order_status === 'delivered' ? 'text-basil' : 'text-flame'}">${o.order_status.replace(/_/g, ' ')}</div>
      </div>
    </button>`).join('');
  box.querySelectorAll('.order-card').forEach(btn => {
    btn.addEventListener('click', () => {
      state.activeOrderId = parseInt(btn.dataset.id, 10);
      state.view = 'order-detail';
      render();
    });
  });
}

async function loadOrderDetail() {
  try {
    const data = await api('GET', `/customer/orders/${state.activeOrderId}`);
    state.activeOrder = data.order;
    state.error = null;
  } catch (e) { state.error = e.message; render(); return; }
  const box = document.getElementById('order-detail-box');
  if (!box) return;
  const o = state.activeOrder;
  const showMap = o.restaurant_location || o.delivery_location || o.rider_location;
  box.innerHTML = `
    <button id="back-to-orders" class="text-sm text-gray-500 mb-3">&larr; Back to orders</button>
    <div class="bg-white rounded-2xl border border-gray-100 p-4 mb-3">
      <div class="font-bold">${o.restaurant_name}</div>
      <div class="text-xs text-gray-500 mt-1">${o.delivery_address}</div>
      <div class="text-sm font-bold mt-3 capitalize">${o.order_status.replace(/_/g, ' ')}</div>
    </div>
    ${showMap ? `<div id="tracking-map" class="rounded-2xl overflow-hidden border border-gray-100 mb-3" style="height:220px;"></div>` : ''}
    <div class="bg-white rounded-2xl border border-gray-100 p-4 mb-3">
      ${o.items.map(i => `<div class="flex justify-between text-sm py-1"><span>${i.item_name} × ${i.quantity}</span><span>${money(i.subtotal)}</span></div>`).join('')}
      <div class="flex justify-between font-bold text-sm pt-2 mt-1 border-t border-gray-100"><span>Total</span><span>${money(o.grand_total)}</span></div>
    </div>
    ${o.tracking_timeline && o.tracking_timeline.length ? `
      <div class="bg-white rounded-2xl border border-gray-100 p-4">
        <div class="text-xs font-bold text-gray-400 uppercase mb-2">Delivery timeline</div>
        ${o.tracking_timeline.map(t => `<div class="text-xs text-gray-600 py-1 flex justify-between"><span class="capitalize">${t.status.replace(/_/g, ' ')}</span><span>${new Date(t.logged_at).toLocaleTimeString()}</span></div>`).join('')}
      </div>` : ''}
    ${o.order_status === 'delivered' ? (o.has_review ? `
      <div class="bg-white rounded-2xl border border-gray-100 p-4 mt-3 text-sm text-basil font-semibold text-center">✓ You rated this order</div>
    ` : `
      <div class="bg-white rounded-2xl border border-gray-100 p-4 mt-3">
        <div class="font-bold text-sm mb-2">Rate this order</div>
        <div id="rating-stars" class="flex gap-1 mb-3">
          ${[1, 2, 3, 4, 5].map(n => `<button data-star="${n}" class="star-btn text-2xl text-gray-300">★</button>`).join('')}
        </div>
        <textarea id="review-comment" placeholder="How was the food? (optional)" class="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm mb-2" rows="2"></textarea>
        <button id="submit-review-btn" class="w-full bg-flame text-white font-bold py-2.5 rounded-xl text-sm">Submit Review</button>
      </div>`) : ''}
  `;
  box.querySelector('#back-to-orders').addEventListener('click', () => { state.view = 'orders'; render(); });

  if (showMap) {
    renderTrackingMap('tracking-map', { restaurant: o.restaurant_location, delivery: o.delivery_location, rider: o.rider_location });
  }
  clearInterval(state.trackingPoll);
  if (o.order_status !== 'delivered' && o.order_status !== 'cancelled') {
    state.trackingPoll = setInterval(async () => {
      if (state.view !== 'order-detail' || state.activeOrderId !== o.order_id) { clearInterval(state.trackingPoll); return; }
      try {
        const fresh = (await api('GET', `/customer/orders/${o.order_id}`)).order;
        if (fresh.rider_location) renderTrackingMap('tracking-map', { restaurant: fresh.restaurant_location, delivery: fresh.delivery_location, rider: fresh.rider_location });
      } catch (e) { /* silent */ }
    }, 12000);
  }

  if (o.order_status === 'delivered' && !o.has_review) {
    let selectedRating = 0;
    const starBtns = box.querySelectorAll('.star-btn');
    starBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        selectedRating = parseInt(btn.dataset.star, 10);
        starBtns.forEach(b => {
          b.className = 'star-btn text-2xl ' + (parseInt(b.dataset.star, 10) <= selectedRating ? 'text-amber-400' : 'text-gray-300');
        });
      });
    });
    box.querySelector('#submit-review-btn').addEventListener('click', async () => {
      if (!selectedRating) { state.error = 'Please select a star rating first.'; render(); return; }
      try {
        await api('POST', `/customer/orders/${o.order_id}/review`, {
          food_rating: selectedRating,
          comment: document.getElementById('review-comment').value,
        });
        state.error = null;
        loadOrderDetail();
      } catch (e) { state.error = e.message; render(); }
    });
  }
}

// ================= Restaurant Dashboard =================

function renderRestaurantDashboard(viewBox) {
  if (state.restaurantView === 'workspace' && state.activeRestaurantId) {
    paintRestaurantWorkspace(viewBox);
  } else {
    viewBox.innerHTML = errorBox() + '<div id="my-restaurants" class="text-sm text-gray-400 text-center py-10">Loading...</div>';
    loadMyRestaurants();
  }
}

async function loadMyRestaurants() {
  try {
    const data = await api('GET', '/restaurant/profile');
    state.myRestaurants = data.restaurants;
    state.error = null;
  } catch (e) { state.error = e.message; render(); return; }
  const box = document.getElementById('my-restaurants');
  if (!box) return;
  box.innerHTML = `
    ${state.myRestaurants.map(r => `
      <button data-id="${r.restaurant_id}" class="my-rest-card w-full text-left bg-white rounded-2xl border border-gray-100 p-4 mb-3 flex items-center justify-between">
        <div>
          <div class="font-bold">${r.name}</div>
          <div class="text-xs text-gray-500 mt-1">${r.city} · ${r.is_open ? 'Open' : 'Closed'}</div>
        </div>
        <span class="text-flame text-sm font-semibold">Manage &rarr;</span>
      </button>`).join('')}
    <div class="bg-white rounded-2xl border border-gray-100 p-4 mt-2">
      <div class="font-bold text-sm mb-3">Add a new restaurant</div>
      <div class="space-y-2">
        <input id="new-rest-name" placeholder="Restaurant name" class="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm">
        <input id="new-rest-address" placeholder="Address" class="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm">
        <input id="new-rest-city" placeholder="City" class="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm">
        <input id="new-rest-cuisine" placeholder="Cuisine type (optional)" class="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm">
        <button id="use-rest-location-btn" type="button" class="text-xs text-flame font-semibold block">📍 Set location (stand at the restaurant, tap this)</button>
        <button id="create-rest-btn" class="w-full bg-flame text-white font-bold py-2.5 rounded-xl text-sm">Create restaurant</button>
      </div>
    </div>`;
  box.querySelectorAll('.my-rest-card').forEach(btn => {
    btn.addEventListener('click', () => {
      state.activeRestaurantId = parseInt(btn.dataset.id, 10);
      state.activeRestaurant = state.myRestaurants.find(r => r.restaurant_id === state.activeRestaurantId);
      state.restaurantView = 'workspace';
      state.restaurantSubview = 'orders';
      render();
    });
  });
  let newRestLat = null, newRestLng = null;
  box.querySelector('#use-rest-location-btn').addEventListener('click', (e) => {
    const btn = e.currentTarget;
    if (!navigator.geolocation) return;
    btn.textContent = 'Getting location...';
    navigator.geolocation.getCurrentPosition(
      (pos) => { newRestLat = pos.coords.latitude; newRestLng = pos.coords.longitude; btn.textContent = '✓ Location set'; btn.className = 'text-xs text-basil font-semibold block'; },
      () => { btn.textContent = '📍 Could not get location — try again'; },
    );
  });
  box.querySelector('#create-rest-btn').addEventListener('click', async () => {
    const body = {
      name: document.getElementById('new-rest-name').value,
      address: document.getElementById('new-rest-address').value,
      city: document.getElementById('new-rest-city').value,
      cuisine_type: document.getElementById('new-rest-cuisine').value,
      latitude: newRestLat, longitude: newRestLng,
    };
    try { await api('POST', '/restaurant/profile', body); state.error = null; render(); }
    catch (e) { state.error = e.message; render(); }
  });
}

function paintRestaurantWorkspace(viewBox) {
  const r = state.activeRestaurant;
  viewBox.innerHTML = `
    <button id="back-to-my-rest" class="text-sm text-gray-500 mb-3">&larr; All restaurants</button>
    <div class="flex items-center justify-between mb-4">
      <div><div class="text-xl font-extrabold">${r.name}</div><div class="text-xs text-gray-500">${r.city}</div></div>
      <button id="toggle-open-btn" class="text-xs font-bold px-3 py-1.5 rounded-lg ${r.is_open ? 'bg-green-50 text-basil' : 'bg-gray-100 text-gray-500'}">${r.is_open ? 'Open' : 'Closed'}</button>
    </div>
    <div class="flex gap-2 mb-4">
      <button data-sub="orders" class="sub-tab flex-1 py-2 rounded-xl text-sm font-semibold ${state.restaurantSubview === 'orders' ? 'bg-flame text-white' : 'bg-white border border-gray-200 text-gray-500'}">Orders</button>
      <button data-sub="menu" class="sub-tab flex-1 py-2 rounded-xl text-sm font-semibold ${state.restaurantSubview === 'menu' ? 'bg-flame text-white' : 'bg-white border border-gray-200 text-gray-500'}">Menu</button>
      <button data-sub="earnings" class="sub-tab flex-1 py-2 rounded-xl text-sm font-semibold ${state.restaurantSubview === 'earnings' ? 'bg-flame text-white' : 'bg-white border border-gray-200 text-gray-500'}">Earnings</button>
    </div>
    ${errorBox()}
    <div id="workspace-body" class="text-sm text-gray-400 text-center py-10">Loading...</div>
  `;
  viewBox.querySelector('#back-to-my-rest').addEventListener('click', () => { state.restaurantView = 'my-restaurants'; render(); });
  viewBox.querySelector('#toggle-open-btn').addEventListener('click', async () => {
    try {
      const data = await api('PATCH', `/restaurant/profile/${r.restaurant_id}/toggle`);
      state.activeRestaurant = data.restaurant;
      render();
    } catch (e) { state.error = e.message; render(); }
  });
  viewBox.querySelectorAll('.sub-tab').forEach(btn => {
    btn.addEventListener('click', () => { state.restaurantSubview = btn.dataset.sub; render(); });
  });

  if (state.restaurantSubview === 'orders') loadRestaurantOrders();
  else if (state.restaurantSubview === 'menu') loadRestaurantMenu();
  else if (state.restaurantSubview === 'earnings') loadRestaurantEarnings();
}

async function loadRestaurantOrders() {
  try {
    const data = await api('GET', `/restaurant/${state.activeRestaurantId}/orders`);
    state.restaurantOrders = data.orders;
    state.error = null;
  } catch (e) { state.error = e.message; render(); return; }
  const box = document.getElementById('workspace-body');
  if (!box) return;
  if (!state.restaurantOrders.length) { box.innerHTML = '<p class="text-gray-400 text-center py-10">No orders yet.</p>'; return; }

  const nextAction = {
    placed: {label: 'Accept', status: 'accepted'},
    accepted: {label: 'Start Preparing', status: 'preparing'},
    preparing: {label: 'Mark Ready for Pickup', status: 'ready_for_pickup'},
  };

  box.innerHTML = state.restaurantOrders.map(o => `
    <div class="bg-white rounded-2xl border border-gray-100 p-4 mb-3">
      <div class="flex justify-between items-start gap-2">
        <div>
          <div class="font-bold text-sm">Order #${o.order_id} — ${o.customer_name || ''}</div>
          <div class="text-xs text-gray-500 mt-1">${o.items.map(i => i.item_name + ' ×' + i.quantity).join(', ')}</div>
          <div class="text-xs text-gray-400 mt-1">${o.delivery_address}</div>
        </div>
        <div class="text-right shrink-0">
          <div class="font-bold text-sm">${money(o.grand_total)}</div>
          <div class="text-xs capitalize font-semibold text-flame mt-1">${o.order_status.replace(/_/g, ' ')}</div>
        </div>
      </div>
      <div class="flex gap-2 mt-3">
        ${nextAction[o.order_status] ? `<button data-id="${o.order_id}" data-status="${nextAction[o.order_status].status}" class="advance-btn flex-1 bg-flame text-white text-xs font-bold py-2 rounded-lg">${nextAction[o.order_status].label}</button>` : ''}
        ${(o.order_status === 'placed' || o.order_status === 'accepted') ? `<button data-id="${o.order_id}" data-status="cancelled" class="advance-btn flex-1 border border-red-200 text-red-500 text-xs font-bold py-2 rounded-lg">Reject</button>` : ''}
      </div>
    </div>`).join('');

  box.querySelectorAll('.advance-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      try {
        await api('PATCH', `/restaurant/orders/${btn.dataset.id}/status`, {status: btn.dataset.status});
        state.error = null;
        loadRestaurantOrders();
      } catch (e) { state.error = e.message; render(); }
    });
  });
}

async function loadRestaurantMenu() {
  try {
    const data = await api('GET', `/restaurant/${state.activeRestaurantId}/menu`);
    state.restaurantMenuItems = data.menu_items;
    state.error = null;
  } catch (e) { state.error = e.message; render(); return; }
  const box = document.getElementById('workspace-body');
  if (!box) return;

  box.innerHTML = `
    <div id="menu-mgmt-list"></div>
    <div class="bg-white rounded-2xl border border-gray-100 p-4 mt-2">
      <div class="font-bold text-sm mb-3">Add menu item</div>
      <div class="space-y-2">
        <input id="new-item-name" placeholder="Item name" class="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm">
        <input id="new-item-price" type="number" placeholder="Price (₹)" class="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm">
        <input id="new-item-category" placeholder="Category (optional)" class="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm">
        <label class="flex items-center gap-2 text-sm text-gray-600"><input id="new-item-veg" type="checkbox" checked> Vegetarian</label>
        <button id="add-item-btn" class="w-full bg-flame text-white font-bold py-2.5 rounded-xl text-sm">Add item</button>
      </div>
    </div>`;

  const listBox = box.querySelector('#menu-mgmt-list');
  if (!state.restaurantMenuItems.length) {
    listBox.innerHTML = '<p class="text-gray-400 text-sm text-center py-6">No items yet — add your first below.</p>';
  } else {
    listBox.innerHTML = state.restaurantMenuItems.map(item => `
      <div class="bg-white rounded-2xl border border-gray-100 p-4 mb-3 flex items-center gap-3">
        ${item.image_url
          ? `<img src="${item.image_url}" class="w-14 h-14 rounded-xl object-cover shrink-0">`
          : `<div class="w-14 h-14 rounded-xl bg-gray-100 flex items-center justify-center text-gray-300 text-[10px] text-center shrink-0">No photo</div>`}
        <div class="flex-1 min-w-0">
          <div class="font-bold text-sm">${item.name} ${item.is_available ? '' : '<span class="text-xs text-gray-400">(unavailable)</span>'}</div>
          <div class="text-sm">${money(item.price)}</div>
        </div>
        <div class="flex flex-col gap-1 shrink-0">
          <button data-id="${item.item_id}" class="photo-btn text-xs font-bold px-3 py-1.5 rounded-lg border border-gray-200 text-gray-500">📷 Photo</button>
          <button data-id="${item.item_id}" class="toggle-item-btn text-xs font-bold px-3 py-1.5 rounded-lg ${item.is_available ? 'bg-green-50 text-basil' : 'bg-gray-100 text-gray-500'}">${item.is_available ? 'Available' : 'Sold out'}</button>
          <button data-id="${item.item_id}" class="delete-item-btn text-xs font-bold px-3 py-1.5 rounded-lg border border-red-200 text-red-500">Delete</button>
        </div>
        <input type="file" accept="image/jpeg,image/png,image/webp" data-id="${item.item_id}" class="photo-input hidden">
      </div>`).join('');
  }

  listBox.querySelectorAll('.toggle-item-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      try { await api('PATCH', `/restaurant/menu-item/${btn.dataset.id}/toggle`); loadRestaurantMenu(); }
      catch (e) { state.error = e.message; render(); }
    });
  });
  listBox.querySelectorAll('.delete-item-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!window.confirm('Delete this item?')) return;
      try { await api('DELETE', `/restaurant/menu-item/${btn.dataset.id}`); loadRestaurantMenu(); }
      catch (e) { state.error = e.message; render(); }
    });
  });
  listBox.querySelectorAll('.photo-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      listBox.querySelector(`.photo-input[data-id="${btn.dataset.id}"]`).click();
    });
  });
  listBox.querySelectorAll('.photo-input').forEach(input => {
    input.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append('photo', file);
      try {
        const headers = {};
        if (state.token) headers['Authorization'] = 'Bearer ' + state.token;
        const res = await fetch(API + `/restaurant/menu-item/${input.dataset.id}/photo`, {
          method: 'POST', headers, body: formData,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Upload failed');
        state.error = null;
        loadRestaurantMenu();
      } catch (err) { state.error = err.message; render(); }
    });
  });
  box.querySelector('#add-item-btn').addEventListener('click', async () => {
    const body = {
      name: document.getElementById('new-item-name').value,
      price: parseFloat(document.getElementById('new-item-price').value),
      category: document.getElementById('new-item-category').value,
      is_veg: document.getElementById('new-item-veg').checked,
    };
    try { await api('POST', `/restaurant/${state.activeRestaurantId}/menu`, body); state.error = null; loadRestaurantMenu(); }
    catch (e) { state.error = e.message; render(); }
  });
}

async function loadRestaurantEarnings() {
  const box = document.getElementById('workspace-body');
  try {
    const data = await api('GET', `/restaurant/${state.activeRestaurantId}/earnings`);
    state.error = null;
    if (!box) return;
    box.innerHTML = `
      <div class="grid grid-cols-2 gap-3">
        <div class="bg-white rounded-2xl border border-gray-100 p-4"><div class="text-xs text-gray-400">Total orders</div><div class="text-2xl font-extrabold mt-1">${data.total_orders}</div></div>
        <div class="bg-white rounded-2xl border border-gray-100 p-4"><div class="text-xs text-gray-400">Delivered</div><div class="text-2xl font-extrabold mt-1 text-basil">${data.delivered_orders}</div></div>
        <div class="bg-white rounded-2xl border border-gray-100 p-4"><div class="text-xs text-gray-400">Active</div><div class="text-2xl font-extrabold mt-1 text-flame">${data.active_orders}</div></div>
        <div class="bg-white rounded-2xl border border-gray-100 p-4"><div class="text-xs text-gray-400">Cancelled</div><div class="text-2xl font-extrabold mt-1 text-gray-400">${data.cancelled_orders}</div></div>
      </div>
      <div class="bg-white rounded-2xl border border-gray-100 p-4 mt-3">
        <div class="text-xs text-gray-400">Total revenue (delivered orders, food value only)</div>
        <div class="text-3xl font-extrabold mt-1">${money(data.total_revenue)}</div>
      </div>`;
  } catch (e) { state.error = e.message; render(); }
}

// ================= Rider Dashboard =================

const CHECKPOINT_SEQUENCE = ['assigned', 'accepted_by_rider', 'reached_restaurant', 'picked_up', 'reached_customer', 'delivered'];
const CHECKPOINT_LABELS = {
  accepted_by_rider: 'Confirm heading out',
  reached_restaurant: 'Reached restaurant',
  picked_up: 'Picked up food',
  reached_customer: 'Reached customer',
  delivered: 'Mark delivered',
};

function nextCheckpointFor(order) {
  const idx = CHECKPOINT_SEQUENCE.indexOf(order.last_checkpoint);
  const nextIdx = idx + 1;
  return nextIdx < CHECKPOINT_SEQUENCE.length ? CHECKPOINT_SEQUENCE[nextIdx] : null;
}

function renderRiderDashboard(viewBox) {
  viewBox.innerHTML = `
    <div class="flex gap-2 mb-4">
      <button data-sub="available" class="rider-tab flex-1 py-2 rounded-xl text-sm font-semibold ${state.riderView === 'available' ? 'bg-flame text-white' : 'bg-white border border-gray-200 text-gray-500'}">Available</button>
      <button data-sub="my-deliveries" class="rider-tab flex-1 py-2 rounded-xl text-sm font-semibold ${state.riderView === 'my-deliveries' ? 'bg-flame text-white' : 'bg-white border border-gray-200 text-gray-500'}">My Deliveries</button>
      <button data-sub="earnings" class="rider-tab flex-1 py-2 rounded-xl text-sm font-semibold ${state.riderView === 'earnings' ? 'bg-flame text-white' : 'bg-white border border-gray-200 text-gray-500'}">Earnings</button>
    </div>
    ${errorBox()}
    <div id="rider-body" class="text-sm text-gray-400 text-center py-10">Loading...</div>
  `;
  viewBox.querySelectorAll('.rider-tab').forEach(btn => {
    btn.addEventListener('click', () => { state.riderView = btn.dataset.sub; render(); });
  });

  if (state.riderView === 'available') loadAvailableOrders();
  else if (state.riderView === 'my-deliveries') loadMyDeliveries();
  else if (state.riderView === 'earnings') loadRiderEarnings();
}

async function loadAvailableOrders() {
  try {
    const data = await api('GET', '/rider/available-orders');
    state.availableOrders = data.available_orders;
    state.error = null;
  } catch (e) { state.error = e.message; render(); return; }
  const box = document.getElementById('rider-body');
  if (!box) return;
  if (!state.availableOrders.length) { box.innerHTML = '<p class="text-gray-400 text-center py-10">No deliveries waiting right now.</p>'; return; }
  box.innerHTML = state.availableOrders.map(o => `
    <div class="bg-white rounded-2xl border border-gray-100 p-4 mb-3">
      <div class="font-bold text-sm">${o.restaurant_name}</div>
      <div class="text-xs text-gray-500 mt-1">${o.restaurant_address || ''}</div>
      <div class="text-xs text-gray-400 mt-1">Deliver to: ${o.delivery_address}</div>
      <div class="flex items-center justify-between mt-3">
        <span class="font-bold text-sm">${money(o.grand_total)}</span>
        <button data-id="${o.order_id}" class="claim-btn bg-flame text-white text-xs font-bold px-4 py-2 rounded-lg">Claim delivery</button>
      </div>
    </div>`).join('');
  box.querySelectorAll('.claim-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      try {
        await api('POST', `/rider/orders/${btn.dataset.id}/claim`);
        state.error = null;
        state.riderView = 'my-deliveries';
        render();
      } catch (e) { state.error = e.message; render(); }
    });
  });
}

async function loadMyDeliveries() {
  try {
    const data = await api('GET', '/rider/my-deliveries');
    state.myDeliveries = data.deliveries;
    state.error = null;
  } catch (e) { state.error = e.message; render(); return; }
  const box = document.getElementById('rider-body');
  if (!box) return;
  if (!state.myDeliveries.length) { box.innerHTML = "<p class=\"text-gray-400 text-center py-10\">You haven't claimed any deliveries yet.</p>"; return; }

  box.innerHTML = state.myDeliveries.map(o => {
    const next = nextCheckpointFor(o);
    const canRelease = o.order_status === 'ready_for_pickup' && o.last_checkpoint !== 'picked_up';
    return `
    <div class="bg-white rounded-2xl border border-gray-100 p-4 mb-3">
      <div class="flex justify-between items-start">
        <div>
          <div class="font-bold text-sm">${o.restaurant_name}</div>
          <div class="text-xs text-gray-500 mt-1">${o.restaurant_address || ''}</div>
          <div class="text-xs text-gray-400 mt-1">To: ${o.delivery_address} · ${o.customer_name} (${o.customer_phone})</div>
        </div>
        <div class="text-right shrink-0">
          <div class="font-bold text-sm">${money(o.grand_total)}</div>
          <div class="text-xs mt-1 capitalize font-semibold ${o.order_status === 'delivered' ? 'text-basil' : 'text-flame'}">${(o.last_checkpoint || 'assigned').replace(/_/g, ' ')}</div>
        </div>
      </div>
      <div class="flex gap-2 mt-3">
        ${next ? `<button data-id="${o.order_id}" data-cp="${next}" class="checkpoint-btn flex-1 bg-flame text-white text-xs font-bold py-2 rounded-lg">${CHECKPOINT_LABELS[next] || next}</button>` : '<span class="flex-1 text-center text-xs text-basil font-bold py-2">Delivered ✓</span>'}
        ${canRelease ? `<button data-id="${o.order_id}" class="release-btn border border-gray-200 text-gray-500 text-xs font-bold px-4 py-2 rounded-lg">Release</button>` : ''}
      </div>
    </div>`;
  }).join('');

  box.querySelectorAll('.checkpoint-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      try {
        await api('PATCH', `/rider/orders/${btn.dataset.id}/checkpoint`, {checkpoint: btn.dataset.cp});
        state.error = null;
        loadMyDeliveries();
      } catch (e) { state.error = e.message; render(); }
    });
  });
  box.querySelectorAll('.release-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!window.confirm('Release this delivery back to the available pool?')) return;
      try {
        await api('POST', `/rider/orders/${btn.dataset.id}/release`, {});
        state.error = null;
        loadMyDeliveries();
      } catch (e) { state.error = e.message; render(); }
    });
  });

  clearInterval(state.locationPingInterval);
  const activeIds = state.myDeliveries.filter(o => o.order_status !== 'delivered').map(o => o.order_id);
  if (activeIds.length && navigator.geolocation) {
    const pingNow = () => {
      if (state.riderView !== 'my-deliveries') { clearInterval(state.locationPingInterval); return; }
      navigator.geolocation.getCurrentPosition((pos) => {
        activeIds.forEach(id => {
          api('POST', `/rider/orders/${id}/location`, {latitude: pos.coords.latitude, longitude: pos.coords.longitude}).catch(() => {});
        });
      }, () => {});
    };
    pingNow();
    state.locationPingInterval = setInterval(pingNow, 20000);
  }
}

async function loadRiderEarnings() {
  try {
    const data = await api('GET', '/rider/earnings');
    state.error = null;
    const box = document.getElementById('rider-body');
    if (!box) return;
    box.innerHTML = `
      <div class="grid grid-cols-2 gap-3">
        <div class="bg-white rounded-2xl border border-gray-100 p-4"><div class="text-xs text-gray-400">Deliveries completed</div><div class="text-2xl font-extrabold mt-1">${data.total_deliveries}</div></div>
        <div class="bg-white rounded-2xl border border-gray-100 p-4"><div class="text-xs text-gray-400">Total earnings</div><div class="text-2xl font-extrabold mt-1 text-basil">${money(data.total_earnings)}</div></div>
      </div>`;
  } catch (e) { state.error = e.message; render(); }
}

document.addEventListener('DOMContentLoaded', () => {
  render();
  setInterval(async () => {
    if (!state.token) return;
    try {
      const data = await api('GET', '/notifications');
      state.unreadCount = data.unread_count;
      updateNotifBadge();
    } catch (e) { /* silent, non-critical */ }
  }, 15000);
});

function updateNotifBadge() {
  const badge = document.getElementById('notif-badge');
  if (!badge) return;
  if (state.unreadCount > 0) {
    badge.textContent = state.unreadCount > 9 ? '9+' : state.unreadCount;
    badge.style.display = 'flex';
  } else {
    badge.style.display = 'none';
  }
}

async function loadNotificationsList() {
  let hadUnread = false;
  try {
    const data = await api('GET', '/notifications');
    state.notifications = data.notifications;
    hadUnread = data.unread_count > 0;
    state.error = null;
  } catch (e) { state.error = e.message; render(); return; }

  const box = document.getElementById('notif-list');
  if (box) {
    if (!state.notifications.length) {
      box.innerHTML = '<p class="text-gray-400 text-center py-10">No notifications yet.</p>';
    } else {
      box.innerHTML = state.notifications.map(n => `
        <div class="bg-white rounded-2xl border ${n.is_read ? 'border-gray-100' : 'border-flame'} p-4 mb-2">
          <div class="flex justify-between items-start gap-2">
            <div class="font-bold text-sm">${n.title}</div>
            ${!n.is_read ? '<span class="w-2 h-2 rounded-full bg-flame shrink-0 mt-1.5"></span>' : ''}
          </div>
          <div class="text-xs text-gray-500 mt-1">${n.message}</div>
          <div class="text-xs text-gray-300 mt-2">${new Date(n.created_at).toLocaleString()}</div>
        </div>`).join('');
    }
  }

  if (hadUnread) {
    try {
      await api('POST', '/notifications/read-all', {});
      state.unreadCount = 0;
      updateNotifBadge();
    } catch (e) { /* silent */ }
  }
}

// ================= Admin Dashboard =================

function renderAdminDashboard(viewBox) {
  viewBox.innerHTML = `
    <div class="flex gap-2 mb-4">
      <button data-sub="pending" class="admin-tab flex-1 py-2 rounded-xl text-sm font-semibold ${state.adminView === 'pending' ? 'bg-flame text-white' : 'bg-white border border-gray-200 text-gray-500'}">Pending Approvals</button>
      <button data-sub="stats" class="admin-tab flex-1 py-2 rounded-xl text-sm font-semibold ${state.adminView === 'stats' ? 'bg-flame text-white' : 'bg-white border border-gray-200 text-gray-500'}">Platform Overview</button>
    </div>
    ${errorBox()}
    <div id="admin-body" class="text-sm text-gray-400 text-center py-10">Loading...</div>
  `;
  viewBox.querySelectorAll('.admin-tab').forEach(btn => {
    btn.addEventListener('click', () => { state.adminView = btn.dataset.sub; render(); });
  });
  if (state.adminView === 'pending') loadPendingApprovals();
  else if (state.adminView === 'stats') loadPlatformStats();
}

async function loadPendingApprovals() {
  try {
    const data = await api('GET', '/admin/pending-approvals');
    state.pendingApprovals = data.pending_approvals;
    state.error = null;
  } catch (e) { state.error = e.message; render(); return; }
  const box = document.getElementById('admin-body');
  if (!box) return;
  if (!state.pendingApprovals.length) { box.innerHTML = '<p class="text-gray-400 text-center py-10">Nothing waiting on approval.</p>'; return; }
  box.innerHTML = state.pendingApprovals.map(u => `
    <div class="bg-white rounded-2xl border border-gray-100 p-4 mb-3 flex items-center justify-between">
      <div>
        <div class="font-bold text-sm">${u.full_name} <span class="text-xs font-normal text-gray-400 capitalize">(${u.role})</span></div>
        <div class="text-xs text-gray-500 mt-1">${u.email} · ${u.phone}</div>
      </div>
      <button data-id="${u.user_id}" class="approve-btn bg-flame text-white text-xs font-bold px-4 py-2 rounded-lg">Approve</button>
    </div>`).join('');
  box.querySelectorAll('.approve-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      try { await api('POST', `/admin/approve/${btn.dataset.id}`, {}); state.error = null; loadPendingApprovals(); }
      catch (e) { state.error = e.message; render(); }
    });
  });
}

async function loadPlatformStats() {
  try {
    const data = await api('GET', '/admin/stats');
    state.error = null;
    const box = document.getElementById('admin-body');
    if (!box) return;
    box.innerHTML = `
      <div class="text-xs font-bold text-gray-400 uppercase mb-2 text-left">Users</div>
      <div class="grid grid-cols-2 gap-3 mb-4">
        <div class="bg-white rounded-2xl border border-gray-100 p-4"><div class="text-xs text-gray-400">Customers</div><div class="text-2xl font-extrabold mt-1">${data.users.customers}</div></div>
        <div class="bg-white rounded-2xl border border-gray-100 p-4"><div class="text-xs text-gray-400">Restaurants</div><div class="text-2xl font-extrabold mt-1">${data.users.restaurants}</div></div>
        <div class="bg-white rounded-2xl border border-gray-100 p-4"><div class="text-xs text-gray-400">Riders</div><div class="text-2xl font-extrabold mt-1">${data.users.riders}</div></div>
        <div class="bg-white rounded-2xl border border-gray-100 p-4"><div class="text-xs text-gray-400">Pending approval</div><div class="text-2xl font-extrabold mt-1 text-flame">${data.users.pending_approval}</div></div>
      </div>
      <div class="text-xs font-bold text-gray-400 uppercase mb-2 text-left">Restaurants</div>
      <div class="grid grid-cols-2 gap-3 mb-4">
        <div class="bg-white rounded-2xl border border-gray-100 p-4"><div class="text-xs text-gray-400">Total</div><div class="text-2xl font-extrabold mt-1">${data.restaurants.total}</div></div>
        <div class="bg-white rounded-2xl border border-gray-100 p-4"><div class="text-xs text-gray-400">Open now</div><div class="text-2xl font-extrabold mt-1 text-basil">${data.restaurants.open_now}</div></div>
      </div>
      <div class="text-xs font-bold text-gray-400 uppercase mb-2 text-left">Orders</div>
      <div class="grid grid-cols-2 gap-3 mb-3">
        <div class="bg-white rounded-2xl border border-gray-100 p-4"><div class="text-xs text-gray-400">Total</div><div class="text-2xl font-extrabold mt-1">${data.orders.total}</div></div>
        <div class="bg-white rounded-2xl border border-gray-100 p-4"><div class="text-xs text-gray-400">Active</div><div class="text-2xl font-extrabold mt-1 text-flame">${data.orders.active}</div></div>
      </div>
      <div class="bg-white rounded-2xl border border-gray-100 p-4">
        <div class="text-xs text-gray-400">Platform GMV (delivered orders)</div>
        <div class="text-3xl font-extrabold mt-1">${money(data.orders.gmv)}</div>
      </div>`;
  } catch (e) { state.error = e.message; render(); }
}
