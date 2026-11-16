#!/usr/bin/env python3
"""Reproducible ShopNest CO3 experiments using Python 3 + SQLite.

The coursework brief permits MySQL or PostgreSQL for the implementation.
This portable experiment runner uses SQLite for locally executable, repeatable
comparisons; MySQL-oriented DDL is supplied separately in SQL/.
"""
from __future__ import annotations
import csv, os, sqlite3, statistics, tempfile, time, json, platform, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DATA = ROOT / "Data"
OUT.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)
SIZES = [1_000, 10_000, 100_000, 1_000_000]
BATCH = 5000


def customer(c): return (c, f"Customer {c:05d}", f"customer{c:05d}@shopnest.test")
def supplier(s): return (s, f"Supplier {s:03d}", f"+91-90000-{s:05d}")
def category(c): return (c, f"Category {c:02d}")
def warehouse(w): return (w, f"Warehouse City {w:02d}")
def product(p):
    cat = (p * 11) % 60 + 1
    sup = (p * 7) % 300 + 1
    return (p, f"Product {p:04d}", round(10.0 + (p % 1000) / 10.0, 2), cat, sup)
def address(c):
    city_no = c % 50 + 1
    street = f"Street {c % 10000 + 1:05d}"
    pin = 600000 + city_no
    city = f"City {city_no:02d}"
    state = f"State {(city_no-1)//10+1:02d}"
    return street, city, pin, state

def row_values(i):
    order = i // 2 + 1
    product_id = (i * 37) % 5000 + 1
    customer_id = (order - 1) % 50000 + 1
    street, city, pin, state = address(customer_id)
    p = product(product_id)
    wh = (i * 13) % 25 + 1
    whcity = f"Warehouse City {wh:02d}"
    return (order, f"2026-{(order%12)+1:02d}-{(order%27)+1:02d}", customer_id,
            f"Customer {customer_id:05d}", f"customer{customer_id:05d}@shopnest.test",
            street, city, pin, state, product_id, p[1], p[2], p[3], f"Category {p[3]:02d}",
            p[4], f"Supplier {p[4]:03d}", f"+91-90000-{p[4]:05d}", (i%5)+1,
            wh, whcity, "eco|fragile|priority", "black|blue")

UNF_SCHEMA = """
CREATE TABLE order_line(
 OrderID INTEGER NOT NULL, OrderDate TEXT NOT NULL, CustomerID INTEGER NOT NULL,
 CustomerName TEXT NOT NULL, CustomerEmail TEXT NOT NULL, ShipStreet TEXT NOT NULL,
 ShipCity TEXT NOT NULL, ShipPIN INTEGER NOT NULL, ShipState TEXT NOT NULL,
 ProductID INTEGER NOT NULL, ProductName TEXT NOT NULL, UnitPrice REAL NOT NULL,
 CategoryID INTEGER NOT NULL, CategoryName TEXT NOT NULL, SupplierID INTEGER NOT NULL,
 SupplierName TEXT NOT NULL, SupplierPhone TEXT NOT NULL, Quantity INTEGER NOT NULL CHECK(Quantity>0),
 WarehouseID INTEGER NOT NULL, WarehouseCity TEXT NOT NULL, TagList TEXT NOT NULL,
 ColourList TEXT NOT NULL, PRIMARY KEY(OrderID, ProductID));
CREATE INDEX ix_unf_supplier ON order_line(SupplierID);
CREATE INDEX ix_unf_order ON order_line(OrderID, ProductID);
"""

NORM_SCHEMA = """
CREATE TABLE customer(CustomerID INTEGER PRIMARY KEY, CustomerName TEXT NOT NULL, CustomerEmail TEXT NOT NULL UNIQUE);
CREATE TABLE supplier(SupplierID INTEGER PRIMARY KEY, SupplierName TEXT NOT NULL, SupplierPhone TEXT NOT NULL);
CREATE TABLE category(CategoryID INTEGER PRIMARY KEY, CategoryName TEXT NOT NULL UNIQUE);
CREATE TABLE warehouse(WarehouseID INTEGER PRIMARY KEY, WarehouseCity TEXT NOT NULL);
CREATE TABLE product(ProductID INTEGER PRIMARY KEY, ProductName TEXT NOT NULL, UnitPrice REAL NOT NULL CHECK(UnitPrice>=0), CategoryID INTEGER NOT NULL REFERENCES category(CategoryID), SupplierID INTEGER NOT NULL REFERENCES supplier(SupplierID));
"""


def create_shipping_order_tables(con, design):
    if design == "3nf":
        con.executescript("""
        CREATE TABLE postal_state(ShipPIN INTEGER PRIMARY KEY, ShipState TEXT NOT NULL);
        CREATE TABLE shipping_address(AddressID INTEGER PRIMARY KEY, ShipStreet TEXT NOT NULL, ShipCity TEXT NOT NULL, ShipPIN INTEGER NOT NULL REFERENCES postal_state(ShipPIN), UNIQUE(ShipStreet,ShipCity), UNIQUE(ShipStreet,ShipPIN));
        """)
    else:
        con.executescript("""
        CREATE TABLE postal_area(ShipPIN INTEGER PRIMARY KEY, ShipCity TEXT NOT NULL, ShipState TEXT NOT NULL);
        CREATE TABLE shipping_address(AddressID INTEGER PRIMARY KEY, ShipStreet TEXT NOT NULL, ShipPIN INTEGER NOT NULL REFERENCES postal_area(ShipPIN), UNIQUE(ShipStreet,ShipPIN));
        """)
    con.executescript("""
    CREATE TABLE orders(OrderID INTEGER PRIMARY KEY, OrderDate TEXT NOT NULL, CustomerID INTEGER NOT NULL REFERENCES customer(CustomerID), AddressID INTEGER NOT NULL REFERENCES shipping_address(AddressID));
    CREATE TABLE order_item(OrderID INTEGER NOT NULL REFERENCES orders(OrderID) ON DELETE RESTRICT, ProductID INTEGER NOT NULL REFERENCES product(ProductID) ON DELETE RESTRICT, Quantity INTEGER NOT NULL CHECK(Quantity>0), WarehouseID INTEGER NOT NULL REFERENCES warehouse(WarehouseID), PRIMARY KEY(OrderID,ProductID));
    CREATE INDEX ix_orders_customer ON orders(CustomerID,OrderDate);
    CREATE INDEX ix_item_product ON order_item(ProductID,OrderID);
    CREATE INDEX ix_item_warehouse ON order_item(WarehouseID);
    """)



def create_norm_extras(con, nf):
    if nf == "3nf":
        con.executescript("""
        CREATE TABLE product_tag_colour(ProductID INTEGER NOT NULL REFERENCES product(ProductID), Tag TEXT NOT NULL, Colour TEXT NOT NULL, PRIMARY KEY(ProductID,Tag,Colour));
        CREATE TABLE supply_triple(SupplierID INTEGER NOT NULL, CategoryID INTEGER NOT NULL, WarehouseID INTEGER NOT NULL, PRIMARY KEY(SupplierID,CategoryID,WarehouseID));
        """)
    else:
        con.executescript("""
        CREATE TABLE product_tag(ProductID INTEGER NOT NULL REFERENCES product(ProductID), Tag TEXT NOT NULL, PRIMARY KEY(ProductID,Tag));
        CREATE TABLE product_colour(ProductID INTEGER NOT NULL REFERENCES product(ProductID), Colour TEXT NOT NULL, PRIMARY KEY(ProductID,Colour));
        CREATE TABLE supply_supplier_category(SupplierID INTEGER NOT NULL, CategoryID INTEGER NOT NULL, PRIMARY KEY(SupplierID,CategoryID));
        CREATE TABLE supply_category_warehouse(CategoryID INTEGER NOT NULL, WarehouseID INTEGER NOT NULL, PRIMARY KEY(CategoryID,WarehouseID));
        CREATE TABLE supply_supplier_warehouse(SupplierID INTEGER NOT NULL, WarehouseID INTEGER NOT NULL, PRIMARY KEY(SupplierID,WarehouseID));
        """)


def seed_dimensions(con, n):
    customer_count=min(50000,(n+1)//2)
    used_products=sorted({(i*37)%5000+1 for i in range(n)})
    used_suppliers=sorted({product(p)[4] for p in used_products})
    used_categories=sorted({product(p)[3] for p in used_products})
    con.executemany("INSERT INTO customer VALUES(?,?,?)", (customer(i) for i in range(1,customer_count+1)))
    con.executemany("INSERT INTO supplier VALUES(?,?,?)", (supplier(i) for i in used_suppliers))
    con.executemany("INSERT INTO category VALUES(?,?)", (category(i) for i in used_categories))
    con.executemany("INSERT INTO warehouse VALUES(?,?)", (warehouse(i) for i in range(1,26)))
    con.executemany("INSERT INTO product VALUES(?,?,?,?,?)", (product(i) for i in used_products))
    pins = {}
    for cid in range(1,customer_count+1):
        st, city, pin, state = address(cid); pins[pin]=(city,state)
    address_map={}
    for cid in range(1,customer_count+1):
        st, city, pin, state=address(cid)
        address_map[(st,city)] = (pin,state)
    address_ids={key: idx+1 for idx,key in enumerate(address_map.keys())}
    return address_ids, address_map, pins


def build_database(path: Path, n: int, design: str):
    con=sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    con.execute("PRAGMA temp_store=MEMORY")
    t0=time.perf_counter()
    if design=="unf":
        con.executescript(UNF_SCHEMA)
        sql="INSERT INTO order_line VALUES(" + ",".join("?" for _ in range(22)) + ")"
        for start in range(0,n,BATCH):
            con.executemany(sql,(row_values(i) for i in range(start,min(start+BATCH,n))))
    else:
        con.executescript(NORM_SCHEMA)
        addrs,address_map,pins=seed_dimensions(con,n)
        create_shipping_order_tables(con,design)
        if design == "3nf":
            # PIN -> state is separated; (street,city) and (street,PIN) are candidate keys.
            con.executemany("INSERT INTO postal_state VALUES(?,?)", ((p,st) for p,(city,st) in pins.items()))
            con.executemany("INSERT INTO shipping_address VALUES(?,?,?,?)",
                ((aid,street,city,pin) for (street,city),(pin,state) in address_map.items() for aid in [addrs[(street,city)]]))
        else:
            con.executemany("INSERT INTO postal_area VALUES(?,?,?)", ((p,city,st) for p,(city,st) in pins.items()))
            con.executemany("INSERT INTO shipping_address VALUES(?,?,?)",
                ((aid,street,pin) for (street,city),(pin,state) in address_map.items() for aid in [addrs[(street,city)]]))
        create_norm_extras(con,design)
        # Independent tag and colour facts, or their Cartesian pairing in the 3NF-only design.
        tags=("eco","fragile","priority")
        colours=("black","blue")
        if design=="3nf":
            con.executemany("INSERT INTO product_tag_colour VALUES(?,?,?)",
                ((p,t,c) for p in sorted({(i*37)%5000+1 for i in range(n)}) for t in tags for c in colours))
            con.executemany("INSERT INTO supply_triple VALUES(?,?,?)", [(1,1,1),(1,3,3),(2,1,2),(2,2,3),(3,1,1),(3,3,3)])
        else:
            con.executemany("INSERT INTO product_tag VALUES(?,?)",((p,t) for p in sorted({(i*37)%5000+1 for i in range(n)}) for t in tags))
            con.executemany("INSERT INTO product_colour VALUES(?,?)",((p,c) for p in sorted({(i*37)%5000+1 for i in range(n)}) for c in colours))
            con.executemany("INSERT INTO supply_supplier_category VALUES(?,?)",[(1,1),(1,3),(2,1),(2,2),(3,1),(3,3)])
            con.executemany("INSERT INTO supply_category_warehouse VALUES(?,?)",[(1,1),(1,2),(2,3),(3,1),(3,3)])
            con.executemany("INSERT INTO supply_supplier_warehouse VALUES(?,?)",[(1,1),(1,3),(2,2),(2,3),(3,1),(3,3)])
        # order and order-item batches: every two item rows share one order id
        for start in range(0,n,BATCH):
            end=min(start+BATCH,n)
            orders=[]; items=[]
            for i in range(start,end):
                order=i//2+1
                p=(i*37)%5000+1
                cid=(order-1)%50000+1
                st,city,pin,state=address(cid)
                addr_id=addrs[(st,city)] # stable surrogate for the customer address
                if i%2==0:
                    orders.append((order,f"2026-{(order%12)+1:02d}-{(order%27)+1:02d}",cid,addr_id))
                wh=(i*13)%25+1
                items.append((order,p,(i%5)+1,wh))
            if orders:
                con.executemany("INSERT INTO orders VALUES(?,?,?,?)",orders)
            con.executemany("INSERT INTO order_item VALUES(?,?,?,?)",items)
    con.commit()
    load_seconds=time.perf_counter()-t0
    page_count=con.execute("PRAGMA page_count").fetchone()[0]
    page_size=con.execute("PRAGMA page_size").fetchone()[0]
    db_bytes=page_count*page_size
    # Use a repeated supplier whose supplier ID occurs in many rows.
    sid=8
    if design=="unf":
        affected=con.execute("SELECT COUNT(*) FROM order_line WHERE SupplierID=?",(sid,)).fetchone()[0]
        timings=[]
        for j in range(3):
            t=time.perf_counter(); con.execute("UPDATE order_line SET SupplierPhone=? WHERE SupplierID=?",(f"+91-81111-{j:05d}",sid)); con.commit(); timings.append(time.perf_counter()-t)
        update_rows=affected
        # five-table order-history query
        q="SELECT o.OrderID,c.CustomerName,p.ProductName,oi.Quantity,s.SupplierName FROM orders o JOIN customer c ON c.CustomerID=o.CustomerID JOIN order_item oi ON oi.OrderID=o.OrderID JOIN product p ON p.ProductID=oi.ProductID JOIN supplier s ON s.SupplierID=p.SupplierID WHERE o.OrderID BETWEEN ? AND ? ORDER BY o.OrderID LIMIT 100"
        query_table="order_line"
    else:
        affected=con.execute("SELECT COUNT(*) FROM order_item oi JOIN product p ON p.ProductID=oi.ProductID WHERE p.SupplierID=?",(sid,)).fetchone()[0]
        timings=[]
        for j in range(3):
            t=time.perf_counter(); con.execute("UPDATE supplier SET SupplierPhone=? WHERE SupplierID=?",(f"+91-81111-{j:05d}",sid)); con.commit(); timings.append(time.perf_counter()-t)
        update_rows=1
        q="SELECT o.OrderID,c.CustomerName,p.ProductName,oi.Quantity,s.SupplierName FROM orders o JOIN customer c ON c.CustomerID=o.CustomerID JOIN order_item oi ON oi.OrderID=o.OrderID JOIN product p ON p.ProductID=oi.ProductID JOIN supplier s ON s.SupplierID=p.SupplierID WHERE o.OrderID BETWEEN ? AND ? ORDER BY o.OrderID LIMIT 100"
        query_table="order_item"
    update_seconds=statistics.median(timings)
    # normalized join test applies to all schemas; for UNF also use an equivalent join via keys.
    # Use normalized schema only for comparison in the query timings; for UNF query the flat table.
    query_times=[]; result_count=0
    for _ in range(5):
        t=time.perf_counter()
        if design=="unf":
            rows=con.execute("SELECT OrderID,CustomerName,ProductName,Quantity,SupplierName FROM order_line WHERE OrderID BETWEEN ? AND ? ORDER BY OrderID LIMIT 100",(max(1,n//8),max(2,n//8+200))).fetchall()
        else:
            rows=con.execute(q,(max(1,n//8),max(2,n//8+200))).fetchall()
        query_times.append(time.perf_counter()-t); result_count=len(rows)
    query_seconds=statistics.median(query_times)
    # For UNF, actual storage bytes are page_count; others as well.
    table_names=[x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    relation_counts={name: con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in table_names}
    result={"rows":n,"design":design,"load_seconds":round(load_seconds,6),"database_bytes":db_bytes,
            "database_mib":round(db_bytes/1024/1024,3),"supplier_8_observation_rows":affected,
            "supplier_update_rows_touched":update_rows,"supplier_update_seconds_median":round(update_seconds,6),
            "history_query_seconds_median":round(query_seconds,6),"history_query_rows_returned":result_count,
            "page_count":page_count,"page_size":page_size,"relation_row_counts":json.dumps(relation_counts,sort_keys=True)}
    con.close()
    return result


def sample_csv():
    path=DATA/"order_line_sample_12.csv"
    headers=["OrderID","OrderDate","CustomerID","CustomerName","CustomerEmail","ShipStreet","ShipCity","ShipPIN","ShipState","ProductID","ProductName","UnitPrice","CategoryID","CategoryName","SupplierID","SupplierName","SupplierPhone","Quantity","WarehouseID","WarehouseCity","TagList","ColourList"]
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(headers)
        for i in range(12): w.writerow(row_values(i))
    return path


def run_tests():
    rows=[]
    with tempfile.TemporaryDirectory(prefix="shopnest_co3_") as td:
        for n in SIZES:
            for d in ("unf","3nf","4nf5nf"):
                p=Path(td)/f"{d}_{n}.sqlite"
                rows.append(build_database(p,n,d))
                p.unlink(missing_ok=True)
    csv_path=OUT/"benchmark_results.csv"
    with csv_path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    # Demonstrate integrity and anomaly logic on a small actual SQLite database.
    demo=OUT/"shopnest_demo.sqlite"
    if demo.exists(): demo.unlink()
    con=sqlite3.connect(demo); con.execute("PRAGMA foreign_keys=ON")
    con.executescript(UNF_SCHEMA)
    for i in range(1000): con.execute("INSERT INTO order_line VALUES("+",".join("?" for _ in range(22))+")",row_values(i))
    con.commit()
    # count repeated supplier fact and update test
    rep=con.execute("SELECT COUNT(*) FROM order_line WHERE SupplierID=8").fetchone()[0]
    before=con.execute("SELECT COUNT(DISTINCT SupplierPhone) FROM order_line WHERE SupplierID=8").fetchone()[0]
    con.execute("UPDATE order_line SET SupplierPhone='+91-79999-00001' WHERE SupplierID=8"); con.commit()
    after=con.execute("SELECT COUNT(DISTINCT SupplierPhone) FROM order_line WHERE SupplierID=8").fetchone()[0]
    anomaly={"UNF_supplier_8_copies":rep,"distinct_phone_values_before":before,"distinct_phone_values_after_consistent_update":after}
    # Constraint test examples on normalized demonstration.
    con2=sqlite3.connect(":memory:"); con2.execute("PRAGMA foreign_keys=ON"); con2.executescript(NORM_SCHEMA); create_shipping_order_tables(con2,"4nf5nf")
    con2.execute("INSERT INTO customer VALUES(1,'Asha Rao','asha@example.test')")
    con2.execute("INSERT INTO supplier VALUES(1,'Supplier 001','9000000001')")
    con2.execute("INSERT INTO category VALUES(1,'Category 01')")
    con2.execute("INSERT INTO warehouse VALUES(1,'Warehouse City 01')")
    con2.execute("INSERT INTO product VALUES(1,'Product 0001',10,1,1)")
    con2.execute("INSERT INTO postal_area VALUES(600001,'City 01','State 01')")
    con2.execute("INSERT INTO shipping_address VALUES(1,'Street 00001',600001)")
    con2.execute("INSERT INTO orders VALUES(1,'2026-01-01',1,1)")
    con2.execute("INSERT INTO order_item VALUES(1,1,2,1)")
    failures=[]
    tests=[("duplicate_order_item", "INSERT INTO order_item VALUES(1,1,3,1)"),
           ("invalid_product_fk", "INSERT INTO order_item VALUES(1,9999,3,1)"),
           ("quantity_check", "INSERT INTO order_item VALUES(1,2,0,1)")]
    for label,sql in tests:
        try: con2.execute(sql); con2.commit(); failures.append((label,"NOT REJECTED"))
        except sqlite3.IntegrityError as e: failures.append((label,str(e))); con2.rollback()
    con.close(); con2.close()
    summary={"environment":{"python":platform.python_version(),"sqlite":sqlite3.sqlite_version,"platform":platform.platform()},
             "anomaly_demo":anomaly,"integrity_tests":failures,"benchmark_rows":len(rows),"sample_csv":str(sample_csv())}
    (OUT/"execution_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    with (OUT/"integrity_tests.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(["test","observed_message"]);w.writerows(failures)
    return rows, summary

if __name__=="__main__":
    rows, summary=run_tests()
    print("SHOPNEST CO3 EXPERIMENT RUN")
    print("Python:",summary["environment"]["python"]," SQLite:",summary["environment"]["sqlite"])
    print("Seeded datasets:",", ".join(str(x) for x in SIZES))
    print("Design runs:",len(rows))
    for r in rows:
        print(f"{r['rows']:>9,} | {r['design']:<7} | load={r['load_seconds']:.4f}s | size={r['database_mib']:.2f} MiB | update_rows={r['supplier_update_rows_touched']} | update={r['supplier_update_seconds_median']:.6f}s | query={r['history_query_seconds_median']:.6f}s")
    print("Integrity tests:")
    for label,msg in summary["integrity_tests"]: print(" -",label,":",msg)
    print("Anomaly demo:",summary["anomaly_demo"])
    print("Outputs saved under outputs/ and Data/.")
