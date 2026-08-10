import sys

path = sys.argv[1] if len(sys.argv) > 1 else "index.html"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

patches = []

# --- 1. Новый чип "Таблетница" в chips-массиве ---
old = '''    {
      label: "Дневник",
      field: "__journal__",
      value: "📔",
      has: true,
    },'''
new = '''    {
      label: "Таблетница",
      field: "__pillboard__",
      value: "💊",
      has: true,
    },
    {
      label: "Дневник",
      field: "__journal__",
      value: "📔",
      has: true,
    },'''
patches.append(("chip_entry", old, new))

# --- 2. Обработчик клика по чипу ---
old = '''  if (chip.dataset.field === "__journal__") {
    openJournalScreen();
    return;
  }'''
new = '''  if (chip.dataset.field === "__pillboard__") {
    openPillboardScreen();
    return;
  }
  if (chip.dataset.field === "__journal__") {
    openJournalScreen();
    return;
  }'''
patches.append(("chip_click_handler", old, new))

# --- 3. HTML-блок экрана: вставляем перед <script src="assets/dial-picker.js"> ---
old = '''<script src="assets/dial-picker.js"></script>'''
new = '''<div id="pillboard-screen">
  <div class="detail-header">
    <button class="detail-back" id="pillboard-back">←</button>
    <div class="detail-title">Таблетница</div>
  </div>
  <div class="detail-body" id="pillboard-body">
    <div style="text-align:center;padding:40px 0;color:var(--text-dim);">Загружаю…</div>
  </div>
</div>

<script src="assets/dial-picker.js"></script>'''
patches.append(("pillboard_html", old, new))

# --- 4. CSS: вставляем перед закрывающим </style> ---
old = '''  .reminder-dismiss {
    background: var(--bg); border: 1px solid var(--border); color: var(--text-dim);
    border-radius: 8px; padding: 5px 10px; font-size: 12px; cursor: pointer;
  }
</style>'''
new = '''  .reminder-dismiss {
    background: var(--bg); border: 1px solid var(--border); color: var(--text-dim);
    border-radius: 8px; padding: 5px 10px; font-size: 12px; cursor: pointer;
  }
  #pillboard-screen { position: fixed; inset: 0; background: var(--bg); z-index: 100; display: none; flex-direction: column; }
  #pillboard-screen.open { display: flex; }
  .pb-slot { border-radius: var(--radius); padding: 14px; margin-bottom: 12px; background: var(--bg-elevated); border: 1px solid var(--border); }
  .pb-slot-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
  .pb-slot-title { font-size: 16px; font-weight: 700; }
  .pb-slot-time { font-size: 12px; color: var(--text-dim); }
  .pb-count { font-size: 12px; font-weight: 700; color: var(--accent); background: rgba(79,184,166,0.12); padding: 3px 8px; border-radius: 10px; }
  .pb-grid { display: flex; flex-wrap: wrap; gap: 8px; }
  .pb-cell {
    width: 74px; height: 90px; background: var(--bg); border-radius: 12px;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    cursor: pointer; position: relative; border: 1px solid var(--border);
    transition: transform 0.15s, opacity 0.3s;
  }
  .pb-cell:active { transform: scale(0.93); }
  .pb-cell.taken { opacity: 0.35; cursor: default; }
  .pb-icon { width: 36px; height: 36px; object-fit: contain; }
  .pb-label { font-size: 9px; color: var(--text-dim); margin-top: 4px; text-align: center; max-width: 66px; }
  .pb-dose { position: absolute; top: 3px; right: 3px; background: var(--bg-elevated); border: 1px solid var(--border);
    border-radius: 10px; font-size: 8px; padding: 2px 4px; color: var(--text); }
  .pb-edit { position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%;
    background: rgba(0,0,0,0.35); color: #fff; font-size: 9px; display: flex; align-items: center; justify-content: center; }
  .pb-add-cell { border: 2px dashed var(--border); color: var(--text-dim); font-size: 24px; }
</style>'''
patches.append(("pillboard_css", old, new))

# --- 5. JS-логика: вставляем перед закрывающим </script> в самом конце файла ---
old = '''    timeInput.value = toHHMM(initMin);
  }
})();
</script>
</body>
</html>'''
new = '''    timeInput.value = toHHMM(initMin);
  }
})();

document.getElementById("pillboard-back").addEventListener("click", () => {
  document.getElementById("pillboard-screen").classList.remove("open");
});

function iconForMed(name) {
  const n = (name || "").toLowerCase();
  if (n.includes("валсартан")) return "assets/pills/tablet_white_plain.png";
  if (n.includes("магни")) return "assets/pills/capsule_white_oblong.png";
  if (n.includes("омега")) return "assets/pills/gel_yellow.png";
  if (n.includes("имован") || n.includes("зопиклон")) return "assets/pills/tablet_white_oval.png";
  if (n.includes("тестостерон") || n.includes("ундеканоат")) return "assets/pills/syringe_blue.png";
  return "assets/pills/tablet_white_plain.png";
}

function bucketTime(t) {
  const h = parseInt((t || "09:00").split(":")[0], 10);
  if (h >= 7 && h < 11) return "morning";
  if (h >= 11 && h < 17) return "day";
  if (h >= 17 && h < 22) return "evening";
  return "night";
}

const PB_SLOT_META = {
  morning: { label: "Утро", time: "07:00 – 11:00" },
  day: { label: "День", time: "11:00 – 17:00" },
  evening: { label: "Вечер", time: "17:00 – 22:00" },
  night: { label: "Ночь", time: "22:00 – 07:00" },
};

async function openPillboardScreen() {
  document.getElementById("pillboard-screen").classList.add("open");
  const body = document.getElementById("pillboard-body");
  try {
    const items = await apiFetch("/therapy/today", { method: "GET" });
    renderPillboard(items);
  } catch (e) {
    body.innerHTML = `<div style="color:var(--text-dim);padding:20px 0;">Не удалось загрузить</div>`;
  }
}

function renderPillboard(items) {
  const slots = {
    morning: { ...PB_SLOT_META.morning, items: [] },
    day: { ...PB_SLOT_META.day, items: [] },
    evening: { ...PB_SLOT_META.evening, items: [] },
    night: { ...PB_SLOT_META.night, items: [] },
  };
  items.forEach(it => slots[bucketTime(it.scheduled_time)].items.push(it));

  const body = document.getElementById("pillboard-body");
  body.innerHTML = Object.entries(slots).map(([key, slot]) => {
    const takenCount = slot.items.filter(i => i.taken).length;
    return `
    <div class="pb-slot">
      <div class="pb-slot-header">
        <div><div class="pb-slot-title">${slot.label}</div><div class="pb-slot-time">${slot.time}</div></div>
        <div class="pb-count">${takenCount}/${slot.items.length}</div>
      </div>
      <div class="pb-grid">
        ${slot.items.map(item => `
          <div class="pb-cell ${item.taken ? 'taken' : ''}" data-id="${item.id}" data-taken="${item.taken}">
            <div class="pb-edit" data-edit-id="${item.id}" data-edit-name="${item.name}">✎</div>
            <img class="pb-icon" src="${iconForMed(item.name)}">
            <div class="pb-label">${item.name}</div>
            <div class="pb-dose">${item.dose || "—"}</div>
          </div>
        `).join("")}
        <div class="pb-cell pb-add-cell" data-add-slot="${key}">+</div>
      </div>
    </div>`;
  }).join("");

  body.querySelectorAll(".pb-cell:not(.pb-add-cell)").forEach(cell => {
    cell.addEventListener("click", async (e) => {
      if (e.target.closest(".pb-edit")) return;
      if (cell.dataset.taken === "true") return;
      const id = cell.dataset.id;
      cell.classList.add("taken");
      cell.dataset.taken = "true";
      try {
        await apiFetch(`/therapy/today/${id}/mark`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ taken: true }),
        });
      } catch (err) {
        cell.classList.remove("taken");
        cell.dataset.taken = "false";
      }
    });
  });

  body.querySelectorAll(".pb-edit").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      openPillEditPrompt(btn.dataset.editId, btn.dataset.editName);
    });
  });

  body.querySelectorAll(".pb-add-cell").forEach(cell => {
    cell.addEventListener("click", () => openPillEditPrompt(null, "", cell.dataset.addSlot));
  });
}

async function openPillEditPrompt(id, currentName, slotKeyForNew) {
  const name = prompt("Название препарата:", currentName || "");
  if (!name) return;
  const dose = prompt("Доза (например ½ табл, 1 капс, 1 мл):", "");
  const time = prompt("Время приёма (HH:MM):", "08:00");
  if (!time) return;

  if (id) {
    await apiFetch(`/therapy/schedules/${id}`, { method: "DELETE" });
  }
  await apiFetch("/therapy/schedules", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, type: "medication", interval_days: 1, times: [time] }),
  });
  if (dose) {
    await apiFetch("/medications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ med_name: name, dose_value: dose, med_type: "other" }),
    });
  }
  openPillboardScreen();
}
</script>
</body>
</html>'''
patches.append(("pillboard_js", old, new))

# --- 6. Тикер: убираем таблетки, оставляем только Ундеканоат ---
old = '''  const parts = [];
  (lastReminders.missing_today || []).forEach(m => parts.push(`Не принял: ${m.med_name}`));
  (lastReminders.injections || []).forEach(i => {
    if (i.days_left <= 0) parts.push(`Пора укол: ${i.compound}`);
    else parts.push(`До укола ${i.compound}: ${i.days_left} дн.`);
  });
  (lastReminders.journal_today || []).forEach(j => parts.push(`Дневник: ${j.text}`));'''
new = '''  const parts = [];
  (lastReminders.injections || []).forEach(i => {
    if (i.compound && i.compound.toLowerCase().includes("ундеканоат")) {
      if (i.days_left <= 0) parts.push(`Пора укол: ${i.compound}`);
      else parts.push(`До укола ${i.compound}: ${i.days_left} дн.`);
    }
  });'''
patches.append(("ticker_filter", old, new))

# --- Применяем с проверкой ---
report = []
for name, old, new in patches:
    count = src.count(old)
    if count != 1:
        print(f"❌ ОШИБКА в патче '{name}': найдено {count} совпадений вместо 1. Патч НЕ применён к файлу.")
        report.append((name, "FAIL", count))
        continue
    src = src.replace(old, new)
    report.append((name, "OK", 1))

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

print("\n--- Отчёт ---")
for name, status, count in report:
    print(f"{status}: {name} ({count} совпадений)")

failed = [r for r in report if r[1] == "FAIL"]
if failed:
    print(f"\n⚠️  {len(failed)} патч(ей) не применились — файл сохранён частично. Проверь вручную.")
    sys.exit(1)
else:
    print("\n✅ Все 6 патчей применены успешно.")
