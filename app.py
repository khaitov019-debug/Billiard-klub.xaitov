import os, sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "club_data.db")
UPLOAD_DIR = os.path.join(BASE, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

def connect():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL DEFAULT '');
    CREATE TABLE IF NOT EXISTS tables(id INTEGER PRIMARY KEY,kind TEXT NOT NULL,number INTEGER NOT NULL,price REAL NOT NULL DEFAULT 30000,active INTEGER NOT NULL DEFAULT 0,started TEXT,paused INTEGER NOT NULL DEFAULT 0,paused_at TEXT,paused_seconds INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,category TEXT NOT NULL,size TEXT NOT NULL DEFAULT '',price REAL NOT NULL DEFAULT 0,cost REAL NOT NULL DEFAULT 0,image TEXT NOT NULL DEFAULT '',active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,table_number INTEGER NOT NULL,started TEXT NOT NULL,ended TEXT NOT NULL,seconds INTEGER NOT NULL,total REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,table_number INTEGER NOT NULL,product_id INTEGER NOT NULL,name TEXT NOT NULL,category TEXT NOT NULL,size TEXT NOT NULL DEFAULT '',qty INTEGER NOT NULL DEFAULT 1,total REAL NOT NULL DEFAULT 0,cost_total REAL NOT NULL DEFAULT 0,created TEXT NOT NULL);
    """)
    for col, definition in [("paused","INTEGER NOT NULL DEFAULT 0"),("paused_at","TEXT"),("paused_seconds","INTEGER NOT NULL DEFAULT 0")]:
        try:
            c.execute(f"ALTER TABLE tables ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError:
            pass
    for key, value in {"club_name":"BILYARD CLUB","login_password":"","admin_password":"","background":""}.items():
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (key,value))
    for i in range(1,6):
        c.execute("INSERT OR IGNORE INTO tables(id,kind,number,price) VALUES(?,?,?,?)", (i,"BILLIARD",i,30000))
    for i in range(1,4):
        c.execute("INSERT OR IGNORE INTO tables(id,kind,number,price) VALUES(?,?,?,?)", (100+i,"TENNIS",i,20000))
    if c.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        products = []
        for name, prices in [("Suv",[3000,5000,7000,9000]),("Coca-Cola",[7000,11000,15000,19000]),("Fanta",[7000,11000,15000,19000]),("Sprite",[7000,11000,15000,19000]),("Pepsi",[7000,11000,15000,19000])]:
            for size, price in zip(["0.5L","1L","1.5L","2L"], prices):
                products.append((name,"Ichimlik",size,price,0))
        products += [("Chips","Gazak","",10000,4000),("Suxarik","Gazak","",8000,3000),("Shokolad","Gazak","",10000,5000),("Yong'oq","Gazak","",15000,8000),("Pullik tayoqcha","Tayoqcha","",5000,0)]
        c.executemany("INSERT INTO products(name,category,size,price,cost) VALUES(?,?,?,?,?)", products)
    c.commit()
    c.close()

init_db()

def now():
    return datetime.now()

def setting(key):
    c=connect()
    row=c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    c.close()
    return row["value"] if row else ""

def set_setting(key, value):
    c=connect()
    c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key,str(value)))
    c.commit()
    c.close()

def money(value):
    return f"{float(value or 0):,.0f}".replace(",", " ") + " so'm"

def elapsed(row):
    if not row["active"] or not row["started"]:
        return 0
    try:
        start=datetime.fromisoformat(row["started"])
        end=datetime.fromisoformat(row["paused_at"]) if row["paused"] and row["paused_at"] else now()
        return max(0, int((end-start).total_seconds())-int(row["paused_seconds"] or 0))
    except Exception:
        return 0

def timer(seconds):
    return f"{seconds//3600:02d}:{(seconds%3600)//60:02d}:{seconds%60:02d}"

def get_tables():
    c=connect()
    rows=c.execute("SELECT * FROM tables ORDER BY CASE kind WHEN 'TENNIS' THEN 0 ELSE 1 END, number").fetchall()
    c.close()
    result=[]
    for row in rows:
        item=dict(row)
        sec=elapsed(row)
        item["seconds"]=sec
        item["timer"]=timer(sec)
        item["table_total"]=money(sec/3600*row["price"])
        result.append(item)
    return result

def require_admin():
    if setting("admin_password") and not session.get("admin_ok"):
        flash("Bu amal uchun admin paroli kerak.")
        return False
    return True

@app.context_processor
def inject_globals():
    return {"club_name":setting("club_name") or "BILYARD CLUB", "money":money, "timer":timer, "setting":setting}

@app.before_request
def login_guard():
    if request.endpoint not in ("login","static") and setting("login_password") and not session.get("logged_in"):
        return redirect(url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form.get("password","")==setting("login_password"):
            session["logged_in"]=True
            return redirect(url_for("home"))
        flash("Parol noto'g'ri.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def home():
    return render_template("index.html", tables=get_tables())

@app.route("/table/<int:table_id>", methods=["GET","POST"])
def table_page(table_id):
    c=connect()
    row=c.execute("SELECT * FROM tables WHERE id=?", (table_id,)).fetchone()
    if not row:
        c.close()
        return redirect(url_for("home"))
    if request.method=="POST":
        action=request.form.get("action")
        if action=="start" and not row["active"]:
            c.execute("UPDATE tables SET active=1,started=?,paused=0,paused_at=NULL,paused_seconds=0 WHERE id=?", (now().isoformat(),table_id))
        elif action=="pause" and row["active"]:
            if not row["paused"]:
                c.execute("UPDATE tables SET paused=1,paused_at=? WHERE id=?", (now().isoformat(),table_id))
            else:
                extra=max(0,int((now()-datetime.fromisoformat(row["paused_at"])).total_seconds())) if row["paused_at"] else 0
                c.execute("UPDATE tables SET paused=0,paused_at=NULL,paused_seconds=paused_seconds+? WHERE id=?", (extra,table_id))
        elif action=="finish" and row["active"]:
            sec=elapsed(row)
            table_total=sec/3600*row["price"]
            ended=now().isoformat()
            c.execute("INSERT INTO sessions(kind,table_number,started,ended,seconds,total) VALUES(?,?,?,?,?,?)", (row["kind"],row["number"],row["started"],ended,sec,table_total))
            sales=c.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE kind=? AND table_number=? AND created>=?", (row["kind"],row["number"],row["started"])).fetchone()[0]
            c.execute("UPDATE tables SET active=0,started=NULL,paused=0,paused_at=NULL,paused_seconds=0 WHERE id=?", (table_id,))
            c.commit()
            c.close()
            flash(f"Stol yakunlandi. Vaqt: {timer(sec)} | Stol: {money(table_total)} | Mahsulotlar: {money(sales)} | JAMI: {money(table_total+sales)}")
            return redirect(url_for("home"))
        elif action=="sell" and row["active"]:
            for field, value in request.form.items():
                if field.startswith("qty_"):
                    try:
                        product_id=int(field[4:])
                        qty=max(0,int(value))
                    except Exception:
                        continue
                    if qty:
                        p=c.execute("SELECT * FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
                        if p:
                            c.execute("INSERT INTO sales(kind,table_number,product_id,name,category,size,qty,total,cost_total,created) VALUES(?,?,?,?,?,?,?,?,?,?)",
                                      (row["kind"],row["number"],p["id"],p["name"],p["category"],p["size"],qty,p["price"]*qty,p["cost"]*qty,now().isoformat()))
        c.commit()
        c.close()
        return redirect(url_for("table_page",table_id=table_id))
    c.close()
    c=connect()
    products=c.execute("SELECT * FROM products WHERE active=1 ORDER BY category,name,size").fetchall()
    sales=c.execute("SELECT name,size,SUM(qty) qty,SUM(total) total FROM sales WHERE kind=? AND table_number=? AND created>=? GROUP BY product_id ORDER BY name,size", (row["kind"],row["number"],row["started"] or "9999")).fetchall()
    c.close()
    return render_template("table.html", row=row, seconds=elapsed(row), products=products, sales=sales)

@app.route("/reports")
def reports():
    period=request.args.get("period","day")
    n=now()
    if period=="week":
        start=(n-timedelta(days=n.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
        title="HAFTALIK"
    elif period=="month":
        start=n.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
        title="OYLIK"
    else:
        start=n.replace(hour=0,minute=0,second=0,microsecond=0)
        title="BUGUNGI"
    s=start.isoformat(); e=n.isoformat()
    c=connect()
    table_total=c.execute("SELECT COALESCE(SUM(total),0) FROM sessions WHERE ended BETWEEN ? AND ?",(s,e)).fetchone()[0]
    sales=c.execute("SELECT COALESCE(SUM(total),0) total,COALESCE(SUM(cost_total),0) cost FROM sales WHERE created BETWEEN ? AND ?",(s,e)).fetchone()
    billiard=c.execute("SELECT COUNT(*) FROM sessions WHERE kind='BILLIARD' AND ended BETWEEN ? AND ?",(s,e)).fetchone()[0]
    tennis=c.execute("SELECT COUNT(*) FROM sessions WHERE kind='TENNIS' AND ended BETWEEN ? AND ?",(s,e)).fetchone()[0]
    water=c.execute("SELECT COALESCE(SUM(qty),0) FROM sales WHERE name='Suv' AND created BETWEEN ? AND ?",(s,e)).fetchone()[0]
    snacks=c.execute("SELECT COALESCE(SUM(qty),0) FROM sales WHERE category='Gazak' AND created BETWEEN ? AND ?",(s,e)).fetchone()[0]
    c.close()
    total=table_total+sales["total"]
    return render_template("reports.html",period=period,title=title,total=total,profit=total-sales["cost"],billiard=billiard,tennis=tennis,water=water,snacks=snacks)

@app.route("/settings", methods=["GET","POST"])
def settings():
    if request.method=="POST":
        if not require_admin():
            return redirect(url_for("settings"))
        if "club_name" in request.form:
            set_setting("club_name",request.form["club_name"].strip() or "BILYARD CLUB")
        if request.form.get("login_password",""):
            set_setting("login_password",request.form["login_password"])
        if request.form.get("admin_password",""):
            set_setting("admin_password",request.form["admin_password"])
        c=connect()
        for field,value in request.form.items():
            if field.startswith("price_"):
                try: c.execute("UPDATE tables SET price=? WHERE id=?", (float(value),int(field[6:])))
                except Exception: pass
            elif field.startswith("prodprice_"):
                try: c.execute("UPDATE products SET price=? WHERE id=?", (float(value),int(field[9:])))
                except Exception: pass
            elif field.startswith("prodcost_"):
                try: c.execute("UPDATE products SET cost=? WHERE id=?", (float(value),int(field[8:])))
                except Exception: pass
        if request.form.get("new_name","").strip():
            try:
                c.execute("INSERT INTO products(name,category,size,price,cost) VALUES(?,?,?,?,?)",
                          (request.form["new_name"].strip(),request.form.get("new_category","Gazak"),request.form.get("new_size",""),float(request.form.get("new_price",0)),float(request.form.get("new_cost",0))))
            except Exception: flash("Mahsulot ma'lumotlarini tekshiring.")
        c.commit();c.close()
        flash("Sozlamalar saqlandi.")
        return redirect(url_for("settings"))
    c=connect()
    tables=c.execute("SELECT * FROM tables ORDER BY kind,number").fetchall()
    products=c.execute("SELECT * FROM products WHERE active=1 ORDER BY category,name,size").fetchall()
    c.close()
    return render_template("settings.html",tables=tables,products=products)

@app.route("/admin-login", methods=["POST"])
def admin_login():
    if not setting("admin_password"):
        session["admin_ok"]=True
    elif request.form.get("password")==setting("admin_password"):
        session["admin_ok"]=True
    else:
        flash("Admin paroli noto'g'ri.")
    return redirect(url_for("settings"))

@app.route("/product/<int:pid>/remove", methods=["POST"])
def remove_product(pid):
    if not require_admin(): return redirect(url_for("settings"))
    c=connect();c.execute("UPDATE products SET active=0 WHERE id=?",(pid,));c.commit();c.close()
    flash("Mahsulot menyudan olib tashlandi.")
    return redirect(url_for("settings"))

if __name__ == "__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
