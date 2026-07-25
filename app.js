const DEMO = {
  orders: [
    {name:"María González", city:"Luque", phone:"0981 000 000", product:"Depiladora IPL", total:"Gs. 450.000", status:"Nuevo", date:"Hoy, 14:20"},
    {name:"Ana Martínez", city:"San Lorenzo", phone:"0982 000 000", product:"Depiladora IPL", total:"Gs. 450.000", status:"Confirmado", date:"Hoy, 12:45"},
    {name:"Laura Benítez", city:"Asunción", phone:"0971 000 000", product:"Depiladora IPL", total:"Gs. 450.000", status:"Nuevo", date:"Ayer, 18:10"},
    {name:"Carolina Rojas", city:"Capiatá", phone:"0983 000 000", product:"Depiladora IPL", total:"Gs. 450.000", status:"Entregado", date:"Ayer, 10:30"}
  ],
  conversations: [
    {id:1, name:"María González", initials:"MG", meta:"Preguntó si realmente funciona", time:"Ahora", preview:"¿Y funciona de verdad?"},
    {id:2, name:"Ana Martínez", initials:"AM", meta:"Interesada en comprar", time:"Hace 12 min", preview:"Bueno, quiero pedir"},
    {id:3, name:"Laura Benítez", initials:"LB", meta:"Consultó por el precio", time:"Hace 28 min", preview:"¿Cuánto sale?"}
  ],
  chats: {
    1: [
      ["customer","Hola, quería saber si funciona de verdad.","14:18"],
      ["bot","Sí, funciona 😊 Es tecnología IPL y además tenés 5 días de garantía para probarla tranquila.","14:19"],
      ["customer","¿Y no irrita la piel?","14:20"],
      ["bot","En general no debería irritar si se usa correctamente. Te explico cómo usarla según tu piel y zona.","14:20"]
    ],
    2: [
      ["customer","Bueno, quiero pedir una.","12:41"],
      ["bot","Perfecto 😊 Para prepararte el pedido, ¿me pasás por favor tu nombre y apellido?","12:42"],
      ["customer","Ana Martínez.","12:43"],
      ["bot","Gracias, Ana. ¿En qué ciudad sería la entrega?","12:43"]
    ],
    3: [
      ["customer","¿Cuánto sale?","17:42"],
      ["bot","Te paso el precio al toque: Gs. 450.000, con pago contra entrega.","17:43"],
      ["customer","Ahh, ¿pago cuando llega entonces?","17:44"],
      ["bot","Exactamente, pagás recién cuando lo tenés en la mano.","17:44"]
    ]
  }
};

let orders = [...DEMO.orders];
let conversations = [...DEMO.conversations];

function showView(view) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active-view"));
  document.getElementById(`${view}-view`).classList.add("active-view");
  document.querySelectorAll(".nav-item").forEach(b => b.classList.toggle("active", b.dataset.view === view));
  const titles = {dashboard:"Resumen del negocio", chat:"Chat en vivo", audit:"Auditor de Fer", orders:"Pedidos", catalog:"Catálogo"};
  document.getElementById("page-title").textContent = titles[view] || "Guaranístore";
}

function renderStats() {
  document.getElementById("stat-orders").textContent = orders.length;
  document.getElementById("stat-today").textContent = orders.filter(o => o.date.includes("Hoy")).length;
  document.getElementById("stat-conversations").textContent = conversations.length;
}

function renderOrders(targetId = "recent-orders", list = orders) {
  const target = document.getElementById(targetId);
  if (!target) return;
  target.innerHTML = list.map(o => targetId === "recent-orders"
    ? `<tr><td>${o.name}</td><td>${o.city}</td><td>${o.product}</td><td><span class="status-badge">${o.status}</span></td><td>${o.date}</td></tr>`
    : `<tr><td>${o.name}</td><td>${o.city}</td><td>${o.phone}</td><td>${o.product}</td><td>${o.total}</td><td><span class="status-badge">${o.status}</span></td><td>${o.date}</td></tr>`
  ).join("");
}

function renderConversations(list = conversations) {
  const el = document.getElementById("conversation-list");
  el.innerHTML = list.map(c => `
    <div class="conversation" data-id="${c.id}">
      <div class="avatar">${c.initials}</div>
      <div class="conversation-info">
        <strong>${c.name}<span class="conversation-time">${c.time}</span></strong>
        <small>${c.preview}</small>
      </div>
    </div>
  `).join("");
  el.querySelectorAll(".conversation").forEach(item => {
    item.addEventListener("click", () => openChat(Number(item.dataset.id)));
  });
}

function openChat(id) {
  const c = conversations.find(x => x.id === id);
  document.querySelectorAll(".conversation").forEach(x => x.classList.toggle("selected", Number(x.dataset.id) === id));
  document.getElementById("chat-customer").textContent = c.name;
  document.getElementById("chat-meta").textContent = c.meta;
  document.getElementById("chat-messages").innerHTML = DEMO.chats[id].map(m => `
    <div class="message ${m[0] === "bot" ? "bot" : "customer"}">
      ${m[1]}<span class="message-meta">${m[2]} · ${m[0] === "bot" ? "Fer" : c.name}</span>
    </div>
  `).join("");
}

function renderCatalog() {
  document.getElementById("catalog-grid").innerHTML = `
    <div class="product-card">
      <div class="product-image">✦</div>
      <div class="product-body">
        <h3>Depiladora IPL</h3>
        <p>Producto conectado al catálogo dinámico de Airtable. En la versión conectada, los datos reales aparecerán automáticamente.</p>
        <div class="product-price">Datos reales desde Airtable</div>
      </div>
    </div>
  `;
}

function initChart() {
  const ctx = document.getElementById("ordersChart");
  if (!ctx || typeof Chart === "undefined") return;
  new Chart(ctx, {
    type: "line",
    data: {
      labels: ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"],
      datasets: [{
        label: "Pedidos",
        data: [2, 4, 3, 6, 5, 8, 4],
        tension: .4,
        fill: true,
        backgroundColor: "rgba(111,75,232,.10)",
        borderColor: "#6f4be8",
        pointRadius: 3
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#eeeae5" } },
        x: { grid: { display: false } }
      }
    }
  });
}

function runAudit() {
  document.getElementById("audit-score").textContent = "86";
  document.getElementById("audit-summary").textContent = "Fer está atendiendo bien en general. Hay una oportunidad clara de mejorar el manejo de objeciones y acelerar algunos cierres.";
  document.getElementById("audit-findings").innerHTML = `
    <div class="finding"><strong>✓ Buena respuesta ante la desconfianza</strong><p>Fer usa correctamente el pago contra entrega para reducir el miedo a comprar online.</p></div>
    <div class="finding"><strong>↗ Oportunidad: preguntar más</strong><p>En algunas conversaciones responde demasiado rápido sin descubrir qué frena realmente al cliente.</p></div>
    <div class="finding"><strong>⚠ Revisar objeciones de precio</strong><p>Conviene reforzar el valor del producto antes de repetir el precio.</p></div>
  `;
}

document.querySelectorAll(".nav-item").forEach(btn => btn.addEventListener("click", () => showView(btn.dataset.view)));
document.querySelectorAll("[data-view-target]").forEach(btn => btn.addEventListener("click", () => showView(btn.dataset.viewTarget)));
document.getElementById("run-audit").addEventListener("click", runAudit);

document.getElementById("conversation-search").addEventListener("input", e => {
  const q = e.target.value.toLowerCase();
  renderConversations(conversations.filter(c => `${c.name} ${c.preview} ${c.meta}`.toLowerCase().includes(q)));
});

document.getElementById("order-search").addEventListener("input", e => {
  const q = e.target.value.toLowerCase();
  renderOrders("orders-table", orders.filter(o => Object.values(o).join(" ").toLowerCase().includes(q)));
});

renderStats();
renderOrders();
renderOrders("orders-table");
renderConversations();
renderCatalog();
initChart();
