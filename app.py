import os, sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(APP_DIR, "club_data.db"))
app = Flask(__name__, template_folder=os.path.join(APP_DIR, "templates"), static_folder=os.path.join(APP_DIR, "static"))
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")

def db():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT '');
    CREATE TABLE IF NOT EXISTS tables(
      id INTEGER PRIMARY KEY, kind TEXT NOT NULL, number INTEGER NOT NULL,
      price REAL NOT NULL DEFAULT 30000, active INTEGER NOT NULL DEFAULT 0,
      started TEXT, paused INTEGER NOT NULL DEFAULT 0, paused_at TEXT,
      paused_seconds INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS products(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL,
      size TEXT NOT NULL DEFAULT '', price REAL NOT NULL DEFAULT 0,
      cost REAL NOT NULL DEFAULT 0, image TEXT NOT NULL DEFAULT '',
      active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS sessions(
      id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, table_number INTEGER NOT NULL,
      started TEXT NOT NULL, ended TEXT NOT NULL, seconds INTEGER NOT NULL, total REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS sales(
      id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, table_number INTEGER NOT NULL,
      product_id INTEGER NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL,
      size TEXT NOT NULL DEFAULT '', qty INTEGER NOT NULL DEFAULT 1,
      total REAL NOT NULL DEFAULT 0, cost_total REAL NOT NULL DEFAULT 0, created TEXT NOT NULL);
    """)
    for col, definition in [("paused","INTEGER NOT NULL DEFAULT 0"),("paused_at","TEXT"),("paused_seconds","INTEGER NOT NULL DEFAULT 0")]:
        try: con.execute(f"ALTER TABLE tables ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError: pass
    defaults = {"club_name":"BILYARD CLUB","login_password":"","admin_password":""}
    for k,v in defaults.items():
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(k,v))
    for i in range(1,6):
        con.execute("INSERT OR IGNORE INTO tables(id,kind,number,price) VALUES(?,?,?,?)",(i,"BILLIARD",i,30000))
    for i in range(1,4):
        con.execute("INSERT OR IGNORE INTO tables(id,kind,number,price) VALUES(?,?,?,?)",(100+i,"TENNIS",i,20000))
    if con.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        items = [
        ("Suv","Ichimlik","0.5L",3000,0),("Suv","Ichimlik","1L",5000,0),("Suv","Ichimlik","1.5L",7000,0),("Suv","Ichimlik","2L",9000,0),
        ("Coca-Cola","Ichimlik","0.5L",7000,0),("Coca-Cola","Ichimlik","1L",11000,0),("Coca-Cola","Ichimlik","1.5L",15000,0),("Coca-Cola","Ichimlik","2L",19000,0),
        ("Fanta","Ichimlik","0.5L",7000,0),("Fanta","Ichimlik","1L",11000,0),("Fanta","Ichimlik","1.5L",15000,0),("Fanta","Ichimlik","2L",19000,0),
        ("Sprite","Ichimlik","0.5L",7000,0),("Sprite","Ichimlik","1L",11000,0),("Sprite","Ichimlik","1.5L",15000,0),("Sprite","Ichimlik","2L",19000,0),
        ("Pepsi","Ichimlik","0.5L",7000,0),("Pepsi","Ichimlik","1L",11000,0),("Pepsi","Ichimlik","1.5L",15000,0),("Pepsi","Ichimlik","2L",19000,0),
        ("Chips","Gazak","",10000,4000),("Suxarik","Gazak","",8000,3000),("Shokolad","Gazak","",10000,5000),("Yong'oq","Gazak","",15000,8000),("Pullik tayoqcha","Tayoqcha","",5000,0)]
        con.executemany("INSERT INTO products(name,category,size,price,cost) VALUES(?,?,?,?,?)",items)
    con.commit()
    con.close()

def money(x): return f"{float(x or 0):,.0f}".replace(","," ") + " so'm"
def elapsed(t):
    if not t["active"] or not t["started"]: return 0
    start = datetime.fromisoformat(t["started"])
    end = datetime.fromisoformat(t["paused_at"]) if t["paused"] and t["paused_at"] else datetime.now()
    return max(0,int((end-start).total_seconds())-int(t["paused_seconds"] or 0))
def fmt(sec): return f"{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}"

@app.context_processor
def inject():
    con=db()
    name=con.execute("SELECT value FROM settings WHERE key='club_name'").fetchone()
    con.close()
    return {"club_name": name["value"] if name else "BILYARD CLUB", "money":money}

@app.route("/")
def home():
    con=db()
    tables=con.execute("SELECT * FROM tables ORDER BY CASE kind WHEN 'TENNIS' THEN 0 ELSE 1 END, number").fetchall()
    products=con.execute("SELECT * FROM products WHERE active=1 ORDER BY category,name,size").fetchall()
    con.close()
    data=[]
    for t in tables:
        d=dict(t); d["elapsed"]=fmt(elapsed(t)); d["charge"]=money(elapsed(t)/3600*t["price"])
        data.append(d)
    return render_template("index.html", tables=data, products=products)

@app.post("/table/<int:tid>/start")
def start(tid):
    con=db(); t=con.execute("SELECT * FROM tables WHERE id=?",(tid,)).fetchone()
    if t and not t["active"]:
        con.execute("UPDATE tables SET active=1,started=?,paused=0,paused_at=NULL,paused_seconds=0 WHERE id=?",(datetime.now().isoformat(),tid))
        con.commit()
    con.close(); return redirect(url_for("home"))

@app.post("/table/<int:tid>/pause")
def pause(tid):
    con=db(); t=con.execute("SELECT * FROM tables WHERE id=?",(tid,)).fetchone()
    if t and t["active"]:
        now=datetime.now()
        if not t["paused"]:
            con.execute("UPDATE tables SET paused=1,paused_at=? WHERE id=?",(now.isoformat(),tid))
        else:
            extra=max(0,int((now-datetime.fromisoformat(t["paused_at"])).total_seconds())) if t["paused_at"] else 0
            con.execute("UPDATE tables SET paused=0,paused_at=NULL,paused_seconds=COALESCE(paused_seconds,0)+? WHERE id=?",(extra,tid))
        con.commit()
    con.close(); return redirect(url_for("home"))

@app.post("/table/<int:tid>/finish")
def finish(tid):
    con=db(); t=con.execute("SELECT * FROM tables WHERE id=?",(tid,)).fetchone()
    if t and t["active"]:
        sec=elapsed(t); ended=datetime.now().isoformat(); total=sec/3600*t["price"]
        con.execute("INSERT INTO sessions(kind,table_number,started,ended,seconds,total) VALUES(?,?,?,?,?,?)",(t["kind"],t["number"],t["started"],ended,sec,total))
        con.execute("UPDATE tables SET active=0,started=NULL,paused=0,paused_at=NULL,paused_seconds=0 WHERE id=?",(tid,))
        con.commit()
        flash(f"Stol yakunlandi. Vaqt: {fmt(sec)}. Stol haqi: {money(total)}")
    con.close(); return redirect(url_for("home"))

@app.post("/sale")
def sale():
    try:
        tid=int(request.form["table_id"]); pid=int(request.form["product_id"]); qty=max(1,int(request.form.get("qty",1)))
    except Exception:
        flash("Mahsulot yoki stol tanlashda xato."); return redirect(url_for("home"))
    con=db(); t=con.execute("SELECT * FROM tables WHERE id=?",(tid,)).fetchone()
    p=con.execute("SELECT * FROM products WHERE id=? AND active=1",(pid,)).fetchone()
    if t and t["active"] and p:
        now=datetime.now().isoformat()
        con.execute("""INSERT INTO sales(kind,table_number,product_id,name,category,size,qty,total,cost_total,created)
        VALUES(?,?,?,?,?,?,?,?,?,?)""",(t["kind"],t["number"],p["id"],p["name"],p["category"],p["size"],qty,p["price"]*qty,p["cost"]*qty,now))
        con.commit(); flash(f"{p['name']} × {qty} qo'shildi.")
    else: flash("Mahsulot qo'shish uchun avval stolni band qiling.")
    con.close(); return redirect(url_for("home"))

@app.route("/reports")
def reports():
    period=request.args.get("period","day")
    now=datetime.now()
    if period=="week": start=(now-timedelta(days=now.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
    elif period=="month": start=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    else: period="day"; start=now.replace(hour=0,minute=0,second=0,microsecond=0)
    s,e=start.isoformat(),now.isoformat(); con=db()
    table_total=con.execute("SELECT COALESCE(SUM(total),0) FROM sessions WHERE ended BETWEEN ? AND ?",(s,e)).fetchone()[0]
    sales=con.execute("SELECT COALESCE(SUM(total),0),COALESCE(SUM(cost_total),0) FROM sales WHERE created BETWEEN ? AND ?",(s,e)).fetchone()
    billiard=con.execute("SELECT COUNT(*) FROM sessions WHERE kind='BILLIARD' AND ended BETWEEN ? AND ?",(s,e)).fetchone()[0]
    tennis=con.execute("SELECT COUNT(*) FROM sessions WHERE kind='TENNIS' AND ended BETWEEN ? AND ?",(s,e)).fetchone()[0]
    water=con.execute("SELECT COALESCE(SUM(qty),0) FROM sales WHERE name='Suv' AND created BETWEEN ? AND ?",(s,e)).fetchone()[0]
    snacks=con.execute("SELECT COALESCE(SUM(qty),0) FROM sales WHERE category='Gazak' AND created BETWEEN ? AND ?",(s,e)).fetchone()[0]
    con.close()
    total=table_total+sales[0]
    return render_template("reports.html",period=period,total=money(total),profit=money(total-sales[1]),billiard=billiard,tennis=tennis,water=water,snacks=snacks)

@app.route("/settings",methods=["GET","POST"])
def settings():
    con=db()
    if request.method=="POST":
        if request.form.get("action")=="club":
            con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('club_name',?)",(request.form.get("club_name","BILYARD CLUB"),))
        elif request.form.get("action")=="price":
            try: con.execute("UPDATE tables SET price=? WHERE id=?",(float(request.form["price"]),int(request.form["table_id"])))
            except Exception: flash("Narx noto'g'ri.")
        elif request.form.get("action")=="product":
            try: con.execute("INSERT INTO products(name,category,size,price,cost) VALUES(?,?,?,?,?)",(request.form["name"],request.form["category"],request.form.get("size",""),float(request.form["price"]),float(request.form.get("cost",0))))
            except Exception: flash("Mahsulot ma'lumotlari xato.")
        elif request.form.get("action")=="product_price":
            try: con.execute("UPDATE products SET price=?,cost=? WHERE id=?",(float(request.form["price"]),float(request.form.get("cost",0)),int(request.form["product_id"])))
            except Exception: flash("Mahsulot narxi xato.")
        con.commit()
        flash("Saqlanmoqda.")
        con.close(); return redirect(url_for("settings"))
    tables=con.execute("SELECT * FROM tables ORDER BY kind,number").fetchall()
    products=con.execute("SELECT * FROM products WHERE active=1 ORDER BY name,size").fetchall()
    con.close()
    return render_template("settings.html",tables=tables,products=products)

@app.get("/api/status")
def status():
    con=db(); rows=con.execute("SELECT * FROM tables").fetchall(); con.close()
    return jsonify({str(t["id"]):{"elapsed":fmt(elapsed(t)),"active":t["active"],"paused":t["paused"],"charge":money(elapsed(t)/3600*t["price"])} for t in rows})

init_db()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
