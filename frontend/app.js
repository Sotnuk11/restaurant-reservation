const API_URL = window.API_URL || 'http://127.0.0.1:5000/api';
let userToken = localStorage.getItem('token');
// The role shown in the UI comes from the signed token, not from editable localStorage.
// The server re-checks the role on every request, so this only controls which buttons are visible.
function roleFromToken(token) {
    try { return JSON.parse(atob(token.split('.')[1])).role || null; } catch { return null; }
}
let userRole = userToken ? roleFromToken(userToken) : null;
let userName = localStorage.getItem('name') || '';
let userPhone = localStorage.getItem('phone') || '';
let currentLang = localStorage.getItem('lang') || 'uk';

// ЗАХИСТ 5: XSS (Cross-Site Scripting) Санітизація
function escapeHTML(str) {
    if (!str) return "";
    return str.replace(/[&<>'"]/g, tag => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'}[tag] || tag));
}

if (localStorage.getItem('theme') === 'dark') document.body.classList.add('dark-mode');
function toggleTheme() {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('theme', document.body.classList.contains('dark-mode') ? 'dark' : 'light');
}

const translations = {
    uk: {
        login_title: "Вхід / Реєстрація", login_btn: "Увійти", register_btn: "Зареєструватися",
        dashboard_title: "Резервація", logout_btn: "Вийти", visit_params: "📅 Параметри:",
        available_tables: "Столики:", my_reservations: "Мої бронювання",
        reg_name_ph: "Ваше ім'я", email_ph: "E-mail (Логін)", pass_ph: "Пароль",
        reg_phone_ph: "Ваш телефон (+48...)",
        guests_ph: "Кількість гостей", phone_ph: "Ваш телефон (+48...)", notes_ph: "Побажання до столика",
        admin_btn: "👑 Адмін Панель", back_btn: "🔙 Повернутися",
        stats_title: "📊 Статистика ресторану", add_table_title: "➕ Додати новий столик",
        table_num_ph: "Номер столика", table_cap_ph: "Кількість місць", table_loc_ph: "Локація (напр. Біля вікна)",
        add_table_btn: "Додати столик", manage_tables_title: "🪑 Управління столиками",
        all_res_title: "📅 Усі бронювання клієнтів", btn_yes: "Так", btn_no: "Ні",
        table_no: "Стіл №", seats: "Місць:", book: "Бронювати", unavailable: "Недоступно",
        select_date: "Оберіть дату та час.", no_res: "Немає бронювань.",
        guests_count: "гостей", cancelled: "Скасовано", cancel_btn: "Скасувати",
        client: "Клієнт:", delete_btn: "Видалити",
        stat_today: "Броней на сьогодні", stat_free: "Вільних столів", stat_total: "Всього броней", stat_users: "Клієнтів",
        err_phone: "Введіть телефон!", err_phone_format: "Некоректний формат телефону (від 9 до 20 цифр)",
        err_name_len: "Ім'я має містити від 2 до 50 символів!", err_pass_len: "Пароль мінімум 8 символів!", err_table: "Заповніть номер та місця",
        msg_success: "Успішно!", msg_added: "Стіл додано!", msg_deleted: "Видалено!",
        msg_login_ok: "Вхід успішний!", msg_session_exp: "Сесія недійсна. Увійдіть заново.",
        conf_cancel: "Скасувати бронь?", conf_delete: "Видалити стіл?"
    },
    pl: {
        login_title: "Logowanie / Rejestracja", login_btn: "Zaloguj", register_btn: "Zarejestruj się",
        dashboard_title: "Rezerwacja", logout_btn: "Wyloguj", visit_params: "📅 Parametry:",
        available_tables: "Dostępne stoliki:", my_reservations: "Moje rezerwacje",
        reg_name_ph: "Twoje imię", email_ph: "E-mail (Login)", pass_ph: "Hasło",
        reg_phone_ph: "Twój numer (+48...)",
        guests_ph: "Liczba gości", phone_ph: "Twój numer (+48...)", notes_ph: "Życzenia specjalne",
        admin_btn: "👑 Panel Admina", back_btn: "🔙 Powrót",
        stats_title: "📊 Statystyki restauracji", add_table_title: "➕ Dodaj nowy stolik",
        table_num_ph: "Numer stolika", table_cap_ph: "Liczba miejsc", table_loc_ph: "Lokalizacja (np. Taras)",
        add_table_btn: "Dodaj stolik", manage_tables_title: "🪑 Zarządzanie stolikami",
        all_res_title: "📅 Wszystkie rezerwacje klientów", btn_yes: "Tak", btn_no: "Nie",
        table_no: "Stolik nr ", seats: "Miejsc:", book: "Rezerwuj", unavailable: "Niedostępne",
        select_date: "Wybierz datę i czas.", no_res: "Brak rezerwacji.",
        guests_count: "gości", cancelled: "Anulowano", cancel_btn: "Anuluj",
        client: "Klient:", delete_btn: "Usuń",
        stat_today: "Rezerwacje dziś", stat_free: "Wolne stoliki", stat_total: "Suma rezerwacji", stat_users: "Klienci",
        err_phone: "Wprowadź numer telefonu!", err_phone_format: "Nieprawidłowy format telefonu (9-20 znaków)",
        err_name_len: "Imię musi mieć od 2 do 50 znaków!", err_pass_len: "Hasło min. 8 znaków!", err_table: "Wypełnij numer i miejsca",
        msg_success: "Sukces!", msg_added: "Stolik dodany!", msg_deleted: "Usunięto!",
        msg_login_ok: "Logowanie udane!", msg_session_exp: "Sesja wygasła. Zaloguj się ponownie.",
        conf_cancel: "Anulować rezerwację?", conf_delete: "Usunąć stolik?"
    },
    en: {
        login_title: "Login / Register", login_btn: "Login", register_btn: "Register",
        dashboard_title: "Reservation", logout_btn: "Logout", visit_params: "📅 Parameters:",
        available_tables: "Available tables:", my_reservations: "My reservations",
        reg_name_ph: "Your name", email_ph: "E-mail (Login)", pass_ph: "Password",
        reg_phone_ph: "Your phone (+48...)",
        guests_ph: "Number of guests", phone_ph: "Your phone (+48...)", notes_ph: "Special requests",
        admin_btn: "👑 Admin Panel", back_btn: "🔙 Go Back",
        stats_title: "📊 Restaurant Statistics", add_table_title: "➕ Add New Table",
        table_num_ph: "Table Number", table_cap_ph: "Capacity", table_loc_ph: "Location (e.g. Window)",
        add_table_btn: "Add Table", manage_tables_title: "🪑 Manage Tables",
        all_res_title: "📅 All Client Reservations", btn_yes: "Yes", btn_no: "No",
        table_no: "Table #", seats: "Seats:", book: "Book", unavailable: "Unavailable",
        select_date: "Select date and time.", no_res: "No reservations.",
        guests_count: "guests", cancelled: "Cancelled", cancel_btn: "Cancel",
        client: "Client:", delete_btn: "Delete",
        stat_today: "Bookings Today", stat_free: "Free Tables", stat_total: "Total Bookings", stat_users: "Customers",
        err_phone: "Enter your phone number!", err_phone_format: "Invalid phone format (9-20 digits)",
        err_name_len: "Name must be 2-50 characters!", err_pass_len: "Password min 8 chars!", err_table: "Fill in number and capacity",
        msg_success: "Success!", msg_added: "Table added!", msg_deleted: "Deleted!",
        msg_login_ok: "Login successful!", msg_session_exp: "Session expired. Please log in again.",
        conf_cancel: "Cancel reservation?", conf_delete: "Delete table?"
    }
};

function applyTranslations() {
    const lang = translations[currentLang];
    document.querySelectorAll('[data-i18n]').forEach(el => {
        if (lang[el.getAttribute('data-i18n')]) el.innerText = lang[el.getAttribute('data-i18n')];
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        if (lang[el.getAttribute('data-i18n-placeholder')]) el.placeholder = lang[el.getAttribute('data-i18n-placeholder')];
    });
}

function changeLanguage(lang) { 
    currentLang = lang; localStorage.setItem('lang', lang); 
    applyTranslations(); 
    if(userToken) { loadTables(); loadReservations(); if(userRole === 'admin') loadAdminData(); }
}
document.getElementById('lang-switch').value = currentLang; applyTranslations();

function showToast(message, type = 'error') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`; toast.innerText = message;
    container.appendChild(toast);
    setTimeout(() => { toast.style.animation = 'fadeOut 0.3s forwards'; setTimeout(() => toast.remove(), 300); }, 3000);
}

function showConfirm(msg, onConfirm) {
    const modal = document.getElementById('custom-confirm');
    document.getElementById('confirm-msg').innerText = msg;
    modal.style.display = 'flex';
    document.getElementById('confirm-yes').onclick = () => { modal.style.display = 'none'; onConfirm(); };
    document.getElementById('confirm-no').onclick = () => { modal.style.display = 'none'; };
}

async function handleResponse(res) {
    const data = await res.json();
    const lang = translations[currentLang];
    if (res.status === 401 || res.status === 403) {
        logout(); showToast(lang.msg_session_exp, 'error'); throw new Error("Unauthorized");
    }
    if (data.status === "error" || !res.ok) throw data;
    return data;
}

// Авторизація
async function register() {
    const lang = translations[currentLang];
    const name = document.getElementById('reg-name').value.trim();
    const phone = document.getElementById('reg-phone').value.trim();
    const pass = document.getElementById('password').value;
    
    if (name.length < 2 || name.length > 50) return showToast(lang.err_name_len);
    if (pass.length < 8) return showToast(lang.err_pass_len);
    if (phone && !/^\+?[0-9\s\-]{9,20}$/.test(phone)) return showToast(lang.err_phone_format);

    try {
        const res = await fetch(`${API_URL}/auth/register`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, phone: phone, email: document.getElementById('email').value, password: pass })
        });
        await handleResponse(res);
        showToast(lang.msg_success, 'success');
    } catch (e) { showToast(e.message, 'error'); }
}

async function login() {
    try {
        const res = await fetch(`${API_URL}/auth/login`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: document.getElementById('email').value, password: document.getElementById('password').value })
        });
        const data = await handleResponse(res);

        localStorage.setItem('phone', data.data.user.phone || '');
userPhone = data.data.user.phone || '';
        
        // Зберігаємо дані в localStorage
        localStorage.setItem('token', data.data.token); 
        localStorage.setItem('role', data.data.user.role); 
        localStorage.setItem('name', data.data.user.name);
        
        userToken = data.data.token; 
        userRole = data.data.user.role; 
        userName = data.data.user.name; 
        userPhone = data.data.user.phone || '';
        
        showDashboard(); 
        showToast(translations[currentLang].msg_login_ok, 'success');
    } catch (e) { showToast(e.message, 'error'); }
}

function logout() {
    localStorage.clear(); userToken = null; userRole = null; userName = null; userPhone = null;
    document.getElementById('auth-section').style.display = 'block'; document.getElementById('dashboard').style.display = 'none';
}

function showDashboard() {
    document.getElementById('auth-section').style.display = 'none';
    document.getElementById('dashboard').style.display = 'block';
    document.getElementById('admin-btn').style.display = userRole === 'admin' ? 'inline-block' : 'none';
    
    // Автоматично підставляємо телефон з локальної пам'яті
    const savedPhone = localStorage.getItem('phone');
    if (savedPhone) {
        document.getElementById('contact-phone').value = savedPhone;
    }
    
    showClientPanel();
}

if (userToken) showDashboard();

function showClientPanel() {
    document.getElementById('client-view').style.display = 'block'; document.getElementById('admin-view').style.display = 'none';
    loadTables(); loadReservations();
}

async function loadTables() {
    if(!userToken) return;
    const lang = translations[currentLang];
    const datetime = document.getElementById('search-date').value;
    const guests = document.getElementById('guest-count').value || 1;
    const container = document.getElementById('tables-container');
    container.innerHTML = '';
    
    if (!datetime) return container.innerHTML = `<p style="grid-column: 1/-1; text-align: center;">${lang.select_date}</p>`;
    const [date, time] = datetime.split('T'); 

    try {
        const res = await fetch(`${API_URL}/tables/available?date=${date}&time=${time}&guests=${guests}`, { headers: { 'Authorization': `Bearer ${userToken}` }});
        const responseData = await handleResponse(res);
        
        responseData.data.forEach(t => {
            const div = document.createElement('div');
            div.className = `card ${t.available ? 'available' : 'booked'}`;
            div.innerHTML = `<strong>${lang.table_no}${t.number}</strong> (${lang.seats} ${t.capacity}) <br>
                             <small>${escapeHTML(t.location)}</small><br>
                             ${t.available ? `<button onclick="reserveTable(${t.id})">${lang.book}</button>` : `<span class="status-booked">${lang.unavailable}</span>`}`;
            container.appendChild(div);
        });
    } catch(e) { console.error(e); }
}

async function loadReservations() {
    if(!userToken) return;
    const lang = translations[currentLang];
    try {
        const res = await fetch(`${API_URL}/reservations/my`, { headers: { 'Authorization': `Bearer ${userToken}` } });
        const responseData = await handleResponse(res); 
        const container = document.getElementById('reservations-container');
        container.innerHTML = '';

        if(responseData.data.length === 0) return container.innerHTML = `<p style="grid-column: 1/-1;">${lang.no_res}</p>`;

        responseData.data.forEach(r => {
            const isCancelled = r.status === 'cancelled';
            const div = document.createElement('div');
            div.className = `card available ${isCancelled ? 'past' : ''}`;
            div.innerHTML = `<strong>${lang.table_no}${r.table_number}</strong> (${r.guests} ${lang.guests_count})<br>
                             <small>${r.date} o ${r.time}</small><br>
                             ${r.notes ? `<small style="color:gray;">💬 ${escapeHTML(r.notes)}</small><br>` : ''}
                             ${isCancelled ? `<i>${lang.cancelled}</i>` : `<button class="btn-danger" onclick="cancelReservation(${r.id})">${lang.cancel_btn}</button>`}`;
            container.appendChild(div);
        });
    } catch(e) { console.error(e); }
}

async function reserveTable(tableId) {
    const lang = translations[currentLang];
    const datetime = document.getElementById('search-date').value;
    const phone = document.getElementById('contact-phone').value.trim();
    const notesInput = document.getElementById('reservation-notes');
    const notes = notesInput ? notesInput.value.trim() : "";
    
    if(!phone) return showToast(lang.err_phone);
    if (!/^\+?[0-9\s\-]{9,20}$/.test(phone)) return showToast(lang.err_phone_format);

    const [date, time] = datetime.split('T');

    try {
        const res = await fetch(`${API_URL}/reservations`, {
            method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${userToken}` },
            body: JSON.stringify({ table_id: tableId, date: date, time: time, guests: document.getElementById('guest-count').value, guest_name: userName, phone: phone, notes: notes })
        });
        await handleResponse(res);
        showToast(lang.msg_success, 'success'); loadTables(); loadReservations();
    } catch(err) { if(err.message) showToast(err.message); }
}

async function cancelReservation(id) {
    const lang = translations[currentLang];
    showConfirm(lang.conf_cancel, async () => {
        try {
            const res = await fetch(`${API_URL}/reservations/${id}/cancel`, { method: 'PATCH', headers: { 'Authorization': `Bearer ${userToken}` }});
            await handleResponse(res);
            showToast(lang.msg_success, 'success'); loadTables(); loadReservations();
        } catch(err) { if(err.message) showToast(err.message); }
    });
}

// Адмін панель
function showAdminPanel() {
    document.getElementById('client-view').style.display = 'none'; document.getElementById('admin-view').style.display = 'block';
    loadAdminData();
}

async function loadAdminData() {
    const lang = translations[currentLang];
    try {
        const resS = await fetch(`${API_URL}/stats`, { headers: { 'Authorization': `Bearer ${userToken}` } });
        const dataS = await handleResponse(resS); const s = dataS.data;
        document.getElementById('admin-stats').innerHTML = `
            <div class="card available" style="flex:1; min-width: 150px; text-align:center;"><h2>${s.today_confirmed}</h2><span>${lang.stat_today}</span></div>
            <div class="card available" style="flex:1; min-width: 150px; text-align:center;"><h2>${s.free_today}</h2><span>${lang.stat_free}</span></div>
            <div class="card available" style="flex:1; min-width: 150px; text-align:center;"><h2>${s.total_confirmed}</h2><span>${lang.stat_total}</span></div>
            <div class="card available" style="flex:1; min-width: 150px; text-align:center;"><h2>${s.total_users}</h2><span>${lang.stat_users}</span></div>
        `;

        const resT = await fetch(`${API_URL}/tables`);
        const dataT = await handleResponse(resT);
        const contT = document.getElementById('admin-tables'); contT.innerHTML='';
        dataT.data.forEach(t => {
            const div = document.createElement('div'); div.className = 'card available';
            div.innerHTML = `<strong>${lang.table_no}${t.number}</strong> (${lang.seats} ${t.capacity})<br><small>${escapeHTML(t.location)}</small> <button class="btn-danger" onclick="deleteTable(${t.id})">${lang.delete_btn}</button>`;
            contT.appendChild(div);
        });

        const resR = await fetch(`${API_URL}/reservations`, { headers: { 'Authorization': `Bearer ${userToken}` } });
        const dataR = await handleResponse(resR);
        const contR = document.getElementById('admin-reservations'); contR.innerHTML='';
        if(dataR.data.length === 0) contR.innerHTML = `<p>${lang.no_res}</p>`;
        dataR.data.forEach(r => {
            const div = document.createElement('div'); div.className = 'card available';
            div.innerHTML = `<strong>${lang.table_no}${r.table_number}</strong><br>${lang.client} <b>${escapeHTML(r.guest_name)}</b><br>☎ ${escapeHTML(r.phone)}<br><small>${r.date} ${r.time} [${r.status}]</small>`;
            contR.appendChild(div);
        });
    } catch(e) { console.error(e); }
}

async function addTable() {
    const lang = translations[currentLang];
    const num = document.getElementById('new-table-num').value;
    const cap = document.getElementById('new-table-capacity').value;
    const loc = document.getElementById('new-table-loc').value.trim();
    if(!num || !cap) return showToast(lang.err_table);
    
    try {
        const res = await fetch(`${API_URL}/tables`, { 
            method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${userToken}` }, 
            body: JSON.stringify({number: num, capacity: cap, location: loc})
        });
        await handleResponse(res);
        showToast(lang.msg_added, 'success'); loadAdminData();
    } catch(err) { if(err.message) showToast(err.message); }
}

async function deleteTable(id) {
    const lang = translations[currentLang];
    showConfirm(lang.conf_delete, async () => {
        try {
            const res = await fetch(`${API_URL}/tables/${id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${userToken}` }});
            await handleResponse(res);
            showToast(lang.msg_deleted, 'success'); loadAdminData();
        } catch(err) { if(err.message) showToast(err.message); }
    });
}