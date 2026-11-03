import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sqlite3
import os
import shutil
from datetime import datetime, timedelta

# =========================================================
# BILYARD CLUB MODERN - 5 BILLIARD + 3 TENNIS
# Ma'lumotlar dastur joylashgan papkadagi ichki DBda saqlanadi.
# Foydalanuvchi DB faylini ochishi shart emas.
# =========================================================

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "club_data.db")
IMG_DIR = os.path.join(APP_DIR, "club_images")
os.makedirs(IMG_DIR, exist_ok=True)

db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.row_factory = sqlite3.Row
db.execute("PRAGMA journal_mode=WAL")

# Eski bazalar uchun pauza ustunlarini qo'shish
for _col, _definition in [
    ("paused", "INTEGER NOT NULL DEFAULT 0"),
    ("paused_at", "TEXT"),
    ("paused_seconds", "INTEGER NOT NULL DEFAULT 0"),
]:
    try:
        db.execute(f"ALTER TABLE tables ADD COLUMN {_col} {_definition}")
    except sqlite3.OperationalError:
        pass
db.commit()

db.executescript("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tables (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    number INTEGER NOT NULL,
    price REAL NOT NULL DEFAULT 30000,
    active INTEGER NOT NULL DEFAULT 0,
    started TEXT,
    paused INTEGER NOT NULL DEFAULT 0,
    paused_at TEXT,
    paused_seconds INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    size TEXT NOT NULL DEFAULT '',
    price REAL NOT NULL DEFAULT 0,
    cost REAL NOT NULL DEFAULT 0,
    image TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    table_number INTEGER NOT NULL,
    started TEXT NOT NULL,
    ended TEXT NOT NULL,
    seconds INTEGER NOT NULL,
    total REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    table_number INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    size TEXT NOT NULL DEFAULT '',
    qty INTEGER NOT NULL DEFAULT 1,
    total REAL NOT NULL DEFAULT 0,
    cost_total REAL NOT NULL DEFAULT 0,
    created TEXT NOT NULL
);
""")

defaults = {
    "club_name": "BILYARD CLUB",
    "background": "",
    "login_password": "",
    "admin_password": ""
}
for k, v in defaults.items():
    db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))

for i in range(1, 6):
    db.execute("INSERT OR IGNORE INTO tables(id,kind,number,price) VALUES(?,?,?,?)",
               (i, "BILLIARD", i, 30000))
for i in range(1, 4):
    db.execute("INSERT OR IGNORE INTO tables(id,kind,number,price) VALUES(?,?,?,?)",
               (100+i, "TENNIS", i, 20000))

if db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
    items = [
        ("Suv","Ichimlik","0.5L",3000,0),
        ("Suv","Ichimlik","1L",5000,0),
        ("Suv","Ichimlik","1.5L",7000,0),
        ("Suv","Ichimlik","2L",9000,0),
        ("Coca-Cola","Ichimlik","0.5L",7000,0),
        ("Coca-Cola","Ichimlik","1L",11000,0),
        ("Coca-Cola","Ichimlik","1.5L",15000,0),
        ("Coca-Cola","Ichimlik","2L",19000,0),
        ("Fanta","Ichimlik","0.5L",7000,0),
        ("Fanta","Ichimlik","1L",11000,0),
        ("Fanta","Ichimlik","1.5L",15000,0),
        ("Fanta","Ichimlik","2L",19000,0),
        ("Sprite","Ichimlik","0.5L",7000,0),
        ("Sprite","Ichimlik","1L",11000,0),
        ("Sprite","Ichimlik","1.5L",15000,0),
        ("Sprite","Ichimlik","2L",19000,0),
        ("Pepsi","Ichimlik","0.5L",7000,0),
        ("Pepsi","Ichimlik","1L",11000,0),
        ("Pepsi","Ichimlik","1.5L",15000,0),
        ("Pepsi","Ichimlik","2L",19000,0),
        ("Chips","Gazak","",10000,4000),
        ("Suxarik","Gazak","",8000,3000),
        ("Shokolad","Gazak","",10000,5000),
        ("Yong'oq","Gazak","",15000,8000),
        ("Pullik tayoqcha","Tayoqcha","",5000,0)
    ]
    db.executemany(
        "INSERT INTO products(name,category,size,price,cost) VALUES(?,?,?,?,?)",
        items
    )
db.commit()

def setting(key):
    r = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else ""

def set_setting(key, value):
    db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
               (key, str(value)))
    db.commit()

def money(v):
    return f"{v:,.0f} so'm".replace(",", " ")

def current_time():
    return datetime.now()

def elapsed(row):
    if not row["active"] or not row["started"]:
        return 0
    try:
        start = datetime.fromisoformat(row["started"])
        paused_seconds = int(row["paused_seconds"] or 0)
        if row["paused"] and row["paused_at"]:
            end = datetime.fromisoformat(row["paused_at"])
        else:
            end = current_time()
        return max(0, int((end - start).total_seconds()) - paused_seconds)
    except Exception:
        return 0

def timer_text(sec):
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def period_start(kind):
    n = current_time()
    if kind == "day":
        return n.replace(hour=0, minute=0, second=0, microsecond=0)
    if kind == "week":
        return (n - timedelta(days=n.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    return n.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

def check_login():
    password = setting("login_password")
    if not password:
        return True
    value = simpledialog.askstring("Kirish", "Kirish paroli:", show="*")
    if value != password:
        messagebox.showerror("Xato", "Parol noto'g'ri.")
        return False
    return True

def check_admin():
    password = setting("admin_password")
    if not password:
        messagebox.showinfo(
            "Admin paroli",
            "Admin paroli hali qo'yilmagan.\n\n"
            "Sozlamalarga kirib, birinchi marta o'zingiz admin parol yarating."
        )
        return False
    value = simpledialog.askstring("Admin", "Admin paroli:", show="*")
    if value != password:
        messagebox.showerror("Xato", "Admin paroli noto'g'ri.")
        return False
    return True

root = tk.Tk()
root.title("BILYARD CLUB")
root.geometry("1500x900")
root.minsize(1100, 700)
root.configure(bg="#0b1118")

style = ttk.Style(root)
try:
    style.theme_use("clam")
except Exception:
    pass

style.configure("TNotebook", background="#0b1118", borderwidth=0)
style.configure("TNotebook.Tab", padding=(18, 9), font=("Segoe UI", 10, "bold"))
style.configure("TCombobox", padding=5)

header = tk.Frame(root, bg="#111a24", height=72)
header.pack(fill="x", side="top")
header.pack_propagate(False)

content = tk.Frame(root, bg="#0b1118")
content.pack(fill="both", expand=True)

status_var = tk.StringVar(value="Tayyor")

def clear_content():
    for w in content.winfo_children():
        w.destroy()

def make_button(parent, text, command, width=16, bg="#1d6fa5"):
    return tk.Button(
        parent, text=text, command=command, width=width,
        bg=bg, fg="white", activebackground="#d6aa35",
        activeforeground="black", font=("Segoe UI", 10, "bold"),
        relief="flat", bd=0, cursor="hand2", padx=10, pady=8
    )

def header_refresh():
    for w in header.winfo_children():
        w.destroy()

    tk.Label(
        header, text=setting("club_name") or "BILYARD CLUB",
        bg="#111a24", fg="#e6b83a",
        font=("Segoe UI", 24, "bold")
    ).pack(side="left", padx=24)

    nav = tk.Frame(header, bg="#111a24")
    nav.pack(side="right", padx=12)

    make_button(nav, "🏠 Bosh sahifa", home, 15, "#173044").pack(side="left", padx=3)
    make_button(nav, "🥤 Menyu", lambda: menu_window(), 12, "#173044").pack(side="left", padx=3)
    make_button(nav, "📊 Tarix", reports, 12, "#173044").pack(side="left", padx=3)
    make_button(nav, "⚙ Sozlamalar", settings, 14, "#173044").pack(side="left", padx=3)

    tk.Label(
        header, textvariable=status_var,
        bg="#111a24", fg="#8fa7b8", font=("Segoe UI", 9)
    ).pack(side="right", padx=15)

def open_table(table_id):
    row = db.execute("SELECT * FROM tables WHERE id=?", (table_id,)).fetchone()
    if not row:
        return

    win = tk.Toplevel(root)
    win.title(f"{row['kind']} {row['number']}")
    win.geometry("1050x720")
    win.minsize(850, 600)
    win.configure(bg="#0b1118")

    top = tk.Frame(win, bg="#13232d", height=100)
    top.pack(fill="x")
    top.pack_propagate(False)

    title_label = tk.Label(top, bg="#13232d", fg="#e6b83a",
                           font=("Segoe UI", 25, "bold"))
    title_label.pack(side="left", padx=25)

    state_label = tk.Label(top, bg="#13232d",
                           font=("Segoe UI", 17, "bold"))
    state_label.pack(side="right", padx=25)

    body = tk.Frame(win, bg="#0b1118")
    body.pack(fill="both", expand=True, padx=20, pady=20)

    left = tk.Frame(body, bg="#13202a")
    left.pack(side="left", fill="both", expand=True, padx=(0,10))

    tk.Label(left, text="VAQT", bg="#13202a", fg="#8fa7b8",
             font=("Segoe UI", 12, "bold")).pack(pady=(25,5))

    timer_label = tk.Label(left, text="00:00:00", bg="#13202a", fg="white",
                           font=("Consolas", 48, "bold"))
    timer_label.pack(pady=10)

    hourly_label = tk.Label(left, bg="#13202a", fg="#d6e1e8",
                            font=("Segoe UI", 13))
    hourly_label.pack(pady=8)

    button_area = tk.Frame(left, bg="#13202a")
    button_area.pack(pady=10)

    right = tk.Frame(body, bg="#13202a")
    right.pack(side="right", fill="both", expand=True, padx=(10,0))

    tk.Label(right, text="STOLGA QO'SHILGAN MAHSULOTLAR",
             bg="#13202a", fg="#e6b83a",
             font=("Segoe UI", 13, "bold")).pack(pady=15)

    sales_frame = tk.Frame(right, bg="#13202a")
    sales_frame.pack(fill="both", expand=True)

    last_button_state = [None]
    last_sales_key = [None]

    def refresh():
        if not win.winfo_exists():
            return

        rr = db.execute("SELECT * FROM tables WHERE id=?", (table_id,)).fetchone()
        if not rr:
            return

        bg = "#5a3a20" if rr["paused"] else ("#3a2025" if rr["active"] else "#13232d")
        top.configure(bg=bg)
        title_label.configure(
            text=f"{'🎱' if rr['kind']=='BILLIARD' else '🏓'} {rr['kind']} {rr['number']}",
            bg=bg
        )

        if rr["paused"]:
            state_label.configure(text="⏸ PAUZA", bg=bg, fg="#ffd166")
        elif rr["active"]:
            state_label.configure(text="🔴 BAND", bg=bg, fg="#ff5d65")
        else:
            state_label.configure(text="🟢 BO'SH", bg=bg, fg="#35d07f")

        # Muhim: faqat timer label yangilanadi, butun oyna qayta yaratilmaydi.
        timer_label.configure(text=timer_text(elapsed(rr)))
        hourly_label.configure(text=f"Stol narxi: {money(rr['price'])} / soat")

        button_state = (bool(rr["active"]), bool(rr["paused"]))
        if button_state != last_button_state[0]:
            last_button_state[0] = button_state
            for w in button_area.winfo_children():
                w.destroy()

            if rr["active"]:
                make_button(
                    button_area,
                    "⏸  PAUZA" if not rr["paused"] else "▶  DAVOM ETTIRISH",
                    lambda: toggle_pause(table_id),
                    22, "#c28724" if not rr["paused"] else "#1d9256"
                ).pack(pady=5)
                make_button(
                    button_area, "⏹  TUGATISH",
                    lambda: finish_table(table_id, win),
                    22, "#a93843"
                ).pack(pady=5)
                make_button(
                    button_area, "🥤  MAHSULOT QO'SHISH",
                    lambda: menu_window(rr["kind"], rr["number"]),
                    22, "#1d6fa5"
                ).pack(pady=5)
            else:
                make_button(
                    button_area, "▶  BAND QILISH",
                    lambda: start_table(table_id, win),
                    22, "#1d9256"
                ).pack(pady=5)

            make_button(button_area, "✖  CHIQISH", win.destroy,
                        22, "#4b5964").pack(pady=5)

        # Mahsulot qo'shilgan zahoti shu oynada ko'rinishi uchun
        # sales jadvalidagi o'zgarishni ham tekshiramiz.
        if rr["started"]:
            sales = db.execute(
                """SELECT name,size,SUM(qty) qty,SUM(total) total
                   FROM sales
                   WHERE kind=? AND table_number=? AND created>=?
                   GROUP BY product_id
                   ORDER BY name,size""",
                (rr["kind"], rr["number"], rr["started"])
            ).fetchall()

            sales_key = tuple(
                (s["name"], s["size"], int(s["qty"]), float(s["total"]))
                for s in sales
            )

            if sales_key != last_sales_key[0]:
                last_sales_key[0] = sales_key

                for w in sales_frame.winfo_children():
                    w.destroy()

                for s in sales:
                    txt = f"{s['name']} {s['size']}  ×{s['qty']}   {money(s['total'])}"
                    tk.Label(
                        sales_frame, text=txt, anchor="w",
                        bg="#13202a", fg="white",
                        font=("Segoe UI", 11)
                    ).pack(fill="x", padx=18, pady=4)
        elif last_sales_key[0] is not None:
            last_sales_key[0] = None
            for w in sales_frame.winfo_children():
                w.destroy()

        if rr["active"]:
            win.after(250, refresh)

    refresh()


def toggle_pause(table_id):
    r = db.execute("SELECT * FROM tables WHERE id=?", (table_id,)).fetchone()
    if not r or not r["active"]:
        return

    now = current_time()

    if not r["paused"]:
        db.execute(
            "UPDATE tables SET paused=1, paused_at=? WHERE id=?",
            (now.isoformat(), table_id)
        )
    else:
        extra = 0
        if r["paused_at"]:
            try:
                extra = max(
                    0,
                    int((now - datetime.fromisoformat(r["paused_at"])).total_seconds())
                )
            except Exception:
                extra = 0

        db.execute(
            """UPDATE tables
               SET paused=0, paused_at=NULL,
                   paused_seconds=COALESCE(paused_seconds,0)+?
               WHERE id=?""",
            (extra, table_id)
        )

    db.commit()

def start_table(table_id, win):
    r = db.execute("SELECT * FROM tables WHERE id=?", (table_id,)).fetchone()
    if not r["active"]:
        db.execute(
            """UPDATE tables
               SET active=1, started=?, paused=0, paused_at=NULL, paused_seconds=0
               WHERE id=?""",
            (current_time().isoformat(), table_id)
        )
        db.commit()
    win.destroy()
    home()

def finish_table(table_id, win):
    r = db.execute("SELECT * FROM tables WHERE id=?", (table_id,)).fetchone()
    if not r["active"]:
        return

    sec = elapsed(r)
    table_total = sec / 3600 * r["price"]
    ended = current_time()

    db.execute(
        """INSERT INTO sessions(kind,table_number,started,ended,seconds,total)
           VALUES(?,?,?,?,?,?)""",
        (r["kind"], r["number"], r["started"], ended.isoformat(), sec, table_total)
    )

    prod = db.execute(
        """SELECT COALESCE(SUM(total),0) total,COALESCE(SUM(cost_total),0) cost
           FROM sales WHERE kind=? AND table_number=? AND created>=?""",
        (r["kind"], r["number"], r["started"])
    ).fetchone()

    db.execute(
        """UPDATE tables
           SET active=0, started=NULL, paused=0, paused_at=NULL, paused_seconds=0
           WHERE id=?""",
        (table_id,)
    )
    db.commit()

    win.destroy()
    messagebox.showinfo(
        "Stol tugadi",
        f"{r['kind']} {r['number']}\n\n"
        f"Vaqt: {timer_text(sec)}\n"
        f"Stol: {money(table_total)}\n"
        f"Mahsulotlar: {money(prod['total'])}\n"
        f"JAMI: {money(table_total + prod['total'])}"
    )
    home()

def add_product_sale(product_id, kind, number):
    p = db.execute("SELECT * FROM products WHERE id=? AND active=1",
                   (product_id,)).fetchone()
    if not p:
        return
    # Mahsulotni faqat faol stolga qo'shish.
    t = db.execute("SELECT * FROM tables WHERE kind=? AND number=?",
                   (kind, number)).fetchone()
    if not t or not t["active"]:
        messagebox.showwarning("Stol", "Avval stolni band qiling.")
        return

    db.execute(
        """INSERT INTO sales(kind,table_number,product_id,name,category,size,qty,total,cost_total,created)
           VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (kind, number, p["id"], p["name"], p["category"], p["size"],
         1, p["price"], p["cost"], current_time().isoformat())
    )
    db.commit()

def menu_window(kind=None, number=None):
    win = tk.Toplevel(root)
    win.title("Menyu")
    win.geometry("1150x760")
    win.minsize(900, 600)
    win.configure(bg="#0b1118")

    title = tk.Frame(win, bg="#111a24", height=75)
    title.pack(fill="x")
    title.pack_propagate(False)
    tk.Label(title, text="🥤  MENYU", bg="#111a24", fg="#e6b83a",
             font=("Segoe UI", 24, "bold")).pack(side="left", padx=25)

    if kind:
        tk.Label(title, text=f"{kind} {number}", bg="#111a24", fg="#9fb3c0",
                 font=("Segoe UI", 12, "bold")).pack(side="left", padx=15)

    area = tk.Frame(win, bg="#0b1118")
    area.pack(fill="both", expand=True, padx=20, pady=15)

    canvas = tk.Canvas(area, bg="#0b1118", highlightthickness=0)
    scroll = ttk.Scrollbar(area, orient="vertical", command=canvas.yview)
    inside = tk.Frame(canvas, bg="#0b1118")
    inside.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0,0), window=inside, anchor="nw")
    canvas.configure(yscrollcommand=scroll.set)
    canvas.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    rows = db.execute(
        "SELECT * FROM products WHERE active=1 ORDER BY category,name,size"
    ).fetchall()

    images = []
    for i, p in enumerate(rows):
        card = tk.Frame(inside, bg="#142531", bd=1, relief="solid")
        card.grid(row=i//4, column=i%4, padx=8, pady=8, sticky="nsew")

        img = None
        path = p["image"]
        if path and os.path.exists(path):
            try:
                img = tk.PhotoImage(file=path)
                # Juda katta PNG bo'lsa kichraytirish.
                w, h = img.width(), img.height()
                if w > 180 or h > 120:
                    factor = max(1, int(max(w/180, h/120)))
                    img = img.subsample(factor, factor)
                images.append(img)
                tk.Label(card, image=img, bg="#142531").pack(pady=8)
            except Exception:
                pass

        tk.Label(
            card,
            text=f"{p['name']} {p['size']}\n{money(p['price'])}",
            bg="#142531", fg="white",
            font=("Segoe UI", 11, "bold"), justify="center"
        ).pack(padx=8, pady=4)

        if kind:
            make_button(
                card, "➕ QO'SHISH",
                lambda pid=p["id"]: add_product_sale(pid, kind, number),
                14, "#1d6fa5"
            ).pack(pady=8)
        else:
            tk.Label(card, text="Stolni tanlab menyuga kiring",
                     bg="#142531", fg="#8fa7b8",
                     font=("Segoe UI", 9)).pack(pady=8)

    for c in range(4):
        inside.grid_columnconfigure(c, weight=1)

    bottom = tk.Frame(win, bg="#0b1118")
    bottom.pack(fill="x", pady=(0,12))
    make_button(bottom, "✖ CHIQISH", win.destroy, 18, "#4b5964").pack()

home_timer_labels = {}
home_state_labels = {}
home_card_frames = {}
home_refresh_job = None

def home():
    global home_refresh_job

    # Eski refresh loop bo'lsa to'xtatamiz.
    if home_refresh_job is not None:
        try:
            root.after_cancel(home_refresh_job)
        except Exception:
            pass
        home_refresh_job = None

    home_timer_labels.clear()
    home_state_labels.clear()
    home_card_frames.clear()

    clear_content()
    header_refresh()

    bg_path = setting("background")
    if bg_path and os.path.exists(bg_path):
        try:
            bg_img = tk.PhotoImage(file=bg_path)
            bg_label = tk.Label(content, image=bg_img)
            bg_label.image = bg_img
            bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)
            bg_label.lower()
        except Exception:
            pass

    title = tk.Label(content, text=setting("club_name") or "BILYARD CLUB",
                     bg="#0b1118", fg="#e6b83a",
                     font=("Segoe UI", 27, "bold"))
    title.pack(pady=(15, 5))

    tk.Label(content, text="Stol ustiga bosib kiring — shu stol ichida boshqarasiz.",
             bg="#0b1118", fg="#9fb3c0",
             font=("Segoe UI", 10)).pack(pady=(0, 12))

    board = tk.Frame(content, bg="#0b1118")
    board.pack(fill="both", expand=True, padx=18, pady=5)

    left = tk.Frame(board, bg="#0b1118", width=280)
    left.pack(side="left", fill="y", padx=(0,8))
    center = tk.Frame(board, bg="#0b1118")
    center.pack(side="left", fill="both", expand=True, padx=8)
    right = tk.Frame(board, bg="#0b1118", width=280)
    right.pack(side="right", fill="y", padx=(8,0))

    def section(parent, label_text):
        tk.Label(parent, text=label_text, bg="#0b1118", fg="#e6b83a",
                 font=("Segoe UI", 14, "bold")).pack(pady=8)

    def table_card(parent, row):
        active = bool(row["active"])
        paused = bool(row["paused"])
        card_bg = "#5a3a20" if paused else ("#3a2025" if active else "#142531")

        card = tk.Frame(parent, bg=card_bg, bd=1, relief="solid")
        card.pack(fill="x", pady=5)

        tk.Label(card, text=f"{'🎱' if row['kind']=='BILLIARD' else '🏓'} "
                           f"{row['kind']} {row['number']}",
                 bg=card_bg, fg="#e6b83a",
                 font=("Segoe UI", 13, "bold")).pack(pady=(8,2))

        timer = tk.Label(card, text=timer_text(elapsed(row)),
                         bg=card_bg, fg="white",
                         font=("Consolas", 20, "bold"))
        timer.pack()

        state = tk.Label(
            card,
            text="⏸ PAUZA" if paused else ("🔴 BAND" if active else "🟢 BO'SH"),
            bg=card_bg,
            fg="#ffd166" if paused else ("#ff5d65" if active else "#35d07f"),
            font=("Segoe UI", 10, "bold")
        )
        state.pack(pady=2)

        home_timer_labels[row["id"]] = timer
        home_state_labels[row["id"]] = state
        home_card_frames[row["id"]] = card

        make_button(card, "KIRISH", lambda tid=row["id"]: open_table(tid),
                    17, "#1d6fa5").pack(pady=(3,8))

    section(left, "🏓 TENNIS — 3 TA")
    for row in db.execute("SELECT * FROM tables WHERE kind='TENNIS' ORDER BY number"):
        table_card(left, row)

    section(center, "🎱 BILLIARD — 5 TA")
    grid = tk.Frame(center, bg="#0b1118")
    grid.pack(fill="both", expand=True)
    rows = db.execute("SELECT * FROM tables WHERE kind='BILLIARD' ORDER BY number").fetchall()
    for i, row in enumerate(rows):
        cell = tk.Frame(grid, bg="#0b1118")
        cell.grid(row=i//2, column=i%2, sticky="nsew", padx=5, pady=5)
        table_card(cell, row)
    grid.grid_columnconfigure(0, weight=1)
    grid.grid_columnconfigure(1, weight=1)

    section(right, "⚡ TEZKOR")
    make_button(right, "🥤 MENYUNI OCHISH", menu_window, 20, "#1d6fa5").pack(pady=6)
    make_button(right, "📊 HISOBOT", reports, 20, "#385a70").pack(pady=6)
    make_button(right, "⚙ SOZLAMALAR", settings, 20, "#385a70").pack(pady=6)

    home_refresh()


def home_refresh():
    global home_refresh_job

    try:
        rows = {
            r["id"]: r
            for r in db.execute(
                "SELECT * FROM tables ORDER BY kind, number"
            ).fetchall()
        }

        active_count = 0

        for table_id, timer_label in list(home_timer_labels.items()):
            if not timer_label.winfo_exists():
                home_timer_labels.pop(table_id, None)
                home_state_labels.pop(table_id, None)
                home_card_frames.pop(table_id, None)
                continue

            row = rows.get(table_id)
            if not row:
                continue

            if row["active"]:
                active_count += 1

            # Faqat label yangilanadi — karta qayta yaratilmaydi.
            timer_label.configure(text=timer_text(elapsed(row)))

            state_label = home_state_labels.get(table_id)
            card = home_card_frames.get(table_id)

            if state_label is not None and state_label.winfo_exists():
                if row["paused"]:
                    state_label.configure(text="⏸ PAUZA", fg="#ffd166")
                elif row["active"]:
                    state_label.configure(text="🔴 BAND", fg="#ff5d65")
                else:
                    state_label.configure(text="🟢 BO'SH", fg="#35d07f")

            if card is not None and card.winfo_exists():
                if row["paused"]:
                    card.configure(bg="#5a3a20")
                    state_label.configure(bg="#5a3a20")
                    timer_label.configure(bg="#5a3a20")
                elif row["active"]:
                    card.configure(bg="#3a2025")
                    state_label.configure(bg="#3a2025")
                    timer_label.configure(bg="#3a2025")
                else:
                    card.configure(bg="#142531")
                    state_label.configure(bg="#142531")
                    timer_label.configure(bg="#142531")

        if "status_var" in globals():
            status_var.set(f"Band stollar: {active_count}")

    except Exception:
        pass

    if root.winfo_exists():
        home_refresh_job = root.after(250, home_refresh)


def reports():
    clear_content()
    header_refresh()

    tk.Label(content, text="📊 HISOBOT", bg="#0b1118", fg="#e6b83a",
             font=("Segoe UI", 27, "bold")).pack(pady=18)

    controls = tk.Frame(content, bg="#0b1118")
    controls.pack(pady=5)

    body = tk.Frame(content, bg="#0b1118")
    body.pack(fill="both", expand=True, padx=35, pady=15)

    def show(kind):
        for w in body.winfo_children():
            w.destroy()

        start = period_start(kind)
        end = current_time()
        s = start.isoformat()
        e = end.isoformat()

        table_total = db.execute(
            "SELECT COALESCE(SUM(total),0) x FROM sessions WHERE ended>=? AND ended<=?",
            (s,e)
        ).fetchone()["x"]

        sales = db.execute(
            "SELECT COALESCE(SUM(total),0) total, COALESCE(SUM(cost_total),0) cost "
            "FROM sales WHERE created>=? AND created<=?", (s,e)
        ).fetchone()

        total = table_total + sales["total"]
        profit = total - sales["cost"]

        billiard_count = db.execute(
            "SELECT COUNT(*) x FROM sessions WHERE kind='BILLIARD' AND ended>=? AND ended<=?",
            (s,e)).fetchone()["x"]
        tennis_count = db.execute(
            "SELECT COUNT(*) x FROM sessions WHERE kind='TENNIS' AND ended>=? AND ended<=?",
            (s,e)).fetchone()["x"]
        water_qty = db.execute(
            "SELECT COALESCE(SUM(qty),0) x FROM sales WHERE name='Suv' AND created>=? AND created<=?",
            (s,e)).fetchone()["x"]
        snack_qty = db.execute(
            "SELECT COALESCE(SUM(qty),0) x FROM sales WHERE category='Gazak' AND created>=? AND created<=?",
            (s,e)).fetchone()["x"]

        label = {"day":"BUGUNGI", "week":"HAFTALIK", "month":"OYLIK"}[kind]

        cards = [
            (f"{label} SAVDO", money(total)),
            (f"{label} SOF FOYDA", money(profit)),
            ("BILLIARD O'YINLARI", f"{billiard_count} ta"),
            ("TENNIS O'YINLARI", f"{tennis_count} ta"),
            ("SUV SOTILDI", f"{water_qty} ta"),
            ("GAZAK SOTILDI", f"{snack_qty} ta"),
        ]

        for i, (name, value) in enumerate(cards):
            card = tk.Frame(body, bg="#142531", bd=1, relief="solid")
            card.grid(row=i//3, column=i%3, padx=8, pady=8, sticky="nsew")
            tk.Label(card, text=name, bg="#142531", fg="#8fa7b8",
                     font=("Segoe UI", 11, "bold")).pack(pady=(18,4))
            tk.Label(card, text=value, bg="#142531", fg="#e6b83a",
                     font=("Segoe UI", 21, "bold")).pack(pady=(0,18))

        for c in range(3):
            body.grid_columnconfigure(c, weight=1)
        for r in range(2):
            body.grid_rowconfigure(r, weight=1)

    for text, kind in [("📅 KUNLIK","day"),("📆 HAFTALIK","week"),("🗓 OYLIK","month")]:
        make_button(controls, text, lambda k=kind: show(k), 16).pack(side="left", padx=5)

    show("day")

def save_password(key, title):
    new = simpledialog.askstring(title, "Yangi parolni kiriting:", show="*")
    if new is None:
        return
    if len(new) < 4:
        messagebox.showwarning("Parol", "Kamida 4 ta belgi bo'lsin.")
        return
    confirm = simpledialog.askstring(title, "Parolni qayta kiriting:", show="*")
    if new != confirm:
        messagebox.showerror("Parol", "Parollar mos kelmadi.")
        return
    set_setting(key, new)
    messagebox.showinfo("Tayyor", "Parol saqlandi.")

def choose_product():
    rows = db.execute("SELECT * FROM products ORDER BY id").fetchall()
    text = "\n".join(
        f"{p['id']} — {p['name']} {p['size']} — {money(p['price'])}"
        for p in rows
    )
    value = simpledialog.askstring("Mahsulot", text + "\n\nMahsulot ID:")
    try:
        return db.execute("SELECT * FROM products WHERE id=?", (int(value),)).fetchone()
    except Exception:
        return None

def product_image():
    if not check_admin():
        return
    p = choose_product()
    if not p:
        return
    f = filedialog.askopenfilename(
        title="Mahsulot rasmini tanlang",
        filetypes=[("PNG/GIF rasm","*.png *.gif")]
    )
    if not f:
        return
    ext = os.path.splitext(f)[1].lower()
    dst = os.path.join(IMG_DIR, f"product_{p['id']}{ext}")
    shutil.copy2(f, dst)
    db.execute("UPDATE products SET image=? WHERE id=?", (dst,p["id"]))
    db.commit()
    messagebox.showinfo("Tayyor", "Mahsulot rasmi saqlandi.")

def background_image():
    if not check_admin():
        return
    f = filedialog.askopenfilename(
        title="Oboy rasmini tanlang",
        filetypes=[("PNG/GIF rasm","*.png *.gif")]
    )
    if not f:
        return
    ext = os.path.splitext(f)[1].lower()
    dst = os.path.join(APP_DIR, "club_background"+ext)
    shutil.copy2(f, dst)
    set_setting("background", dst)
    messagebox.showinfo("Tayyor", "Oboy saqlandi.")
    home()

def edit_product_price():
    if not check_admin():
        return
    p = choose_product()
    if not p:
        return
    value = simpledialog.askstring("Narx", "Yangi sotuv narxi:",
                                   initialvalue=str(p["price"]))
    try:
        price = float(value)
        db.execute("UPDATE products SET price=? WHERE id=?", (price,p["id"]))
        db.commit()
    except Exception:
        messagebox.showerror("Xato", "Narx noto'g'ri.")

def edit_product_cost():
    if not check_admin():
        return
    p = choose_product()
    if not p:
        return
    value = simpledialog.askstring("Tannarx", "Mahsulot tannarxi:",
                                   initialvalue=str(p["cost"]))
    try:
        cost = float(value)
        db.execute("UPDATE products SET cost=? WHERE id=?", (cost,p["id"]))
        db.commit()
    except Exception:
        messagebox.showerror("Xato", "Tannarx noto'g'ri.")

def add_product():
    if not check_admin():
        return
    name = simpledialog.askstring("Mahsulot", "Nomi:")
    if not name:
        return
    cat = simpledialog.askstring("Mahsulot", "Kategoriya (Ichimlik/Gazak/Tayoqcha):") or "Gazak"
    size = simpledialog.askstring("Mahsulot", "Hajmi (masalan 0.5L):") or ""
    price = simpledialog.askstring("Mahsulot", "Sotuv narxi:") or "0"
    cost = simpledialog.askstring("Mahsulot", "Tannarxi:") or "0"
    try:
        db.execute(
            "INSERT INTO products(name,category,size,price,cost) VALUES(?,?,?,?,?)",
            (name,cat,size,float(price),float(cost))
        )
        db.commit()
        messagebox.showinfo("Tayyor", "Mahsulot qo'shildi.")
    except Exception:
        messagebox.showerror("Xato", "Ma'lumot noto'g'ri.")

def remove_product():
    if not check_admin():
        return
    p = choose_product()
    if p:
        db.execute("UPDATE products SET active=0 WHERE id=?", (p["id"],))
        db.commit()
        messagebox.showinfo("Tayyor", "Mahsulot menyudan olib tashlandi.")

def edit_table_prices(parent):
    for w in parent.winfo_children():
        w.destroy()

    tk.Label(parent, text="STOL NARXLARI", bg="#0b1118", fg="#e6b83a",
             font=("Segoe UI", 15, "bold")).pack(pady=10)

    rows = db.execute("SELECT * FROM tables ORDER BY kind,number").fetchall()
    for r in rows:
        line = tk.Frame(parent, bg="#0b1118")
        line.pack(fill="x", pady=3)
        tk.Label(line, text=f"{r['kind']} {r['number']}", width=20,
                 bg="#0b1118", fg="white", anchor="w").pack(side="left")
        ent = tk.Entry(line, width=15)
        ent.insert(0, str(r["price"]))
        ent.pack(side="left")
        def save(tid=r["id"], e=ent):
            try:
                db.execute("UPDATE tables SET price=? WHERE id=?",
                           (float(e.get()),tid))
                db.commit()
                messagebox.showinfo("Tayyor", "Stol narxi saqlandi.")
            except Exception:
                messagebox.showerror("Xato", "Narx noto'g'ri.")
        make_button(line, "SAQLASH", save, 11).pack(side="left", padx=8)

def settings():
    clear_content()
    header_refresh()

    tk.Label(content, text="⚙ SOZLAMALAR", bg="#0b1118", fg="#e6b83a",
             font=("Segoe UI", 27, "bold")).pack(pady=15)

    outer = tk.Frame(content, bg="#0b1118")
    outer.pack(fill="both", expand=True, padx=35)

    left = tk.Frame(outer, bg="#13202a")
    left.pack(side="left", fill="y", padx=(0,10))
    right = tk.Frame(outer, bg="#13202a")
    right.pack(side="left", fill="both", expand=True, padx=(10,0))

    tk.Label(left, text="Dastur", bg="#13202a", fg="#e6b83a",
             font=("Segoe UI", 15, "bold")).pack(pady=15)

    name_entry = tk.Entry(left, width=30)
    name_entry.insert(0, setting("club_name"))
    name_entry.pack(pady=5)
    make_button(left, "KLUB NOMINI SAQLASH",
                lambda: (set_setting("club_name",name_entry.get()),
                         header_refresh(), home()),
                24).pack(pady=7)

    make_button(left, "🖼 OBOY RASMI", background_image, 24, "#1d6fa5").pack(pady=7)
    make_button(left, "🖼 MAHSULOT RASMI", product_image, 24, "#1d6fa5").pack(pady=7)
    make_button(left, "➕ MAHSULOT QO'SHISH", add_product, 24).pack(pady=7)
    make_button(left, "💰 SOTUV NARXINI O'ZGARTIRISH",
                edit_product_price, 24).pack(pady=7)
    make_button(left, "📦 TANNARXNI O'ZGARTIRISH",
                edit_product_cost, 24).pack(pady=7)
    make_button(left, "🗑 MAHSULOTNI OLIB TASHLASH",
                remove_product, 24, "#a93843").pack(pady=7)

    tk.Frame(left, bg="#263b48", height=1).pack(fill="x", padx=15, pady=15)
    make_button(left, "🔐 KIRISH PAROLI", 
                lambda: save_password("login_password","Kirish paroli"),
                24).pack(pady=7)
    make_button(left, "🔑 ADMIN PAROLI",
                lambda: save_password("admin_password","Admin paroli"),
                24).pack(pady=7)

    tk.Label(right, text="Stol narxlarini o'zgartirish",
             bg="#13202a", fg="#e6b83a",
             font=("Segoe UI", 15, "bold")).pack(pady=10)

    price_area = tk.Frame(right, bg="#0b1118")
    price_area.pack(fill="both", expand=True, padx=20, pady=10)
    edit_table_prices(price_area)

def alarm_check():
    # Har bir faol stolning to'liq soat chegarasiga kirganda signal.
    for r in db.execute("SELECT * FROM tables WHERE active=1"):
        s = elapsed(r)
        if s > 0 and s % 3600 == 0:
            try:
                root.bell()
            except Exception:
                pass
    root.after(1000, alarm_check)

def close_app():
    try:
        db.commit()
        db.close()
    finally:
        root.destroy()

# Birinchi ishga tushirishda login paroli bo'lmasa hech narsa so'ramaydi.
if not check_login():
    root.destroy()
else:
    root.protocol("WM_DELETE_WINDOW", close_app)
    home()
    alarm_check()
    root.mainloop()
