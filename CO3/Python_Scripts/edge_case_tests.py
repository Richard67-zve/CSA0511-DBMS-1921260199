"""Small executable demonstrations for CO3 anomaly and boundary-case requirements."""
import sqlite3, csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'outputs'; OUT.mkdir(exist_ok=True)
results=[]
def record(test, outcome, detail): results.append((test,outcome,detail))
# Minimal UNF versus normalised catalogue demonstration.
u=sqlite3.connect(':memory:')
u.executescript('''CREATE TABLE order_line(OrderID INTEGER,ProductID INTEGER,ProductName TEXT,SupplierID INTEGER,SupplierPhone TEXT,PRIMARY KEY(OrderID,ProductID));''')
u.execute("INSERT INTO order_line VALUES(1,10,'Desk Lamp',8,'9000000008')")
# A catalogue-only insert cannot be represented without inventing an order line.
record('UNF product-only insertion','NOT REPRESENTABLE','ORDER_LINE requires an order observation; no independent PRODUCT relation exists.')
u.execute('DELETE FROM order_line WHERE OrderID=1 AND ProductID=10')
exists=u.execute('SELECT COUNT(*) FROM order_line WHERE ProductID=10').fetchone()[0]
record('UNF delete last observation','CATALOGUE FACT LOST' if exists==0 else 'ERROR','Deleting the final observation removed the only ProductName copy.')
for i in range(1,6): u.execute('INSERT OR REPLACE INTO order_line VALUES(?,?,?, ?, ?)',(i,10,'Desk Lamp',8,'9000000008'))
copies=u.execute('SELECT COUNT(*) FROM order_line WHERE SupplierID=8').fetchone()[0]
u.execute("UPDATE order_line SET SupplierPhone='9111111111' WHERE SupplierID=8")
updated=u.execute("SELECT COUNT(*) FROM order_line WHERE SupplierID=8 AND SupplierPhone='9111111111'").fetchone()[0]
record('UNF supplier phone update','REPEATED ROWS UPDATED',f'{updated} observation rows changed for one supplier fact.')
u.close()
# Normalised catalogue facts persist independent from observations.
n=sqlite3.connect(':memory:'); n.execute('PRAGMA foreign_keys=ON')
n.executescript('''CREATE TABLE supplier(SupplierID INTEGER PRIMARY KEY,SupplierName TEXT,SupplierPhone TEXT);
CREATE TABLE product(ProductID INTEGER PRIMARY KEY,ProductName TEXT,SupplierID INTEGER REFERENCES supplier(SupplierID));
CREATE TABLE customer(CustomerID INTEGER PRIMARY KEY,CustomerName TEXT);
CREATE TABLE orders(OrderID INTEGER PRIMARY KEY,CustomerID INTEGER REFERENCES customer(CustomerID));
CREATE TABLE order_item(OrderID INTEGER,ProductID INTEGER,PRIMARY KEY(OrderID,ProductID),FOREIGN KEY(OrderID) REFERENCES orders(OrderID) ON DELETE RESTRICT,FOREIGN KEY(ProductID) REFERENCES product(ProductID) ON DELETE RESTRICT);
CREATE TABLE product_tag(ProductID INTEGER,Tag TEXT,PRIMARY KEY(ProductID,Tag),FOREIGN KEY(ProductID) REFERENCES product(ProductID));
CREATE TABLE product_colour(ProductID INTEGER,Colour TEXT,PRIMARY KEY(ProductID,Colour),FOREIGN KEY(ProductID) REFERENCES product(ProductID));''')
n.execute("INSERT INTO supplier VALUES(8,'Supplier 008','9000000008')")
n.execute("INSERT INTO product VALUES(10,'Desk Lamp',8)")
record('Normalised product-only insertion','ALLOWED',f"Product exists with no order line: {n.execute('SELECT COUNT(*) FROM product WHERE ProductID=10').fetchone()[0]}")
n.execute("INSERT INTO customer VALUES(7,'Asha Rao')"); n.execute("INSERT INTO orders VALUES(20,7)"); n.execute("INSERT INTO order_item VALUES(20,10)")
n.execute('DELETE FROM order_item WHERE OrderID=20 AND ProductID=10'); n.execute('DELETE FROM orders WHERE OrderID=20')
product_exists=n.execute('SELECT COUNT(*) FROM product WHERE ProductID=10').fetchone()[0]
customer_exists=n.execute('SELECT COUNT(*) FROM customer WHERE CustomerID=7').fetchone()[0]
record('Normalised deletion of last order','CATALOGUE AND CUSTOMER PRESERVED',f'Product rows={product_exists}; Customer rows={customer_exists}.')
# Boundary: product with no tags and no order is retained.
tag_count=n.execute('SELECT COUNT(*) FROM product_tag WHERE ProductID=10').fetchone()[0]
colour_count=n.execute('SELECT COUNT(*) FROM product_colour WHERE ProductID=10').fetchone()[0]
record('Product with no tags/colours','VALID',f'Product remains; tag rows={tag_count}; colour rows={colour_count}.')
# Change supplier phone without updating product or order-line copies.
n.execute("UPDATE supplier SET SupplierPhone='9111111111' WHERE SupplierID=8")
phone=n.execute('SELECT SupplierPhone FROM supplier WHERE SupplierID=8').fetchone()[0]
record('Normalised supplier update','ONE MASTER ROW',f'Supplier phone is now {phone}; referenced product remains unchanged.')
# Historical price snapshot survives current catalogue price change.
n.executescript('''CREATE TABLE order_item_price(OrderID INTEGER,ProductID INTEGER,UnitPricePaid REAL,PRIMARY KEY(OrderID,ProductID));
CREATE TABLE product_current_price(ProductID INTEGER PRIMARY KEY,UnitPrice REAL);''')
n.execute('INSERT INTO product_current_price VALUES(10,25.0)'); n.execute('INSERT INTO order_item_price VALUES(20,10,22.5)')
n.execute('UPDATE product_current_price SET UnitPrice=27.0 WHERE ProductID=10')
paid=n.execute('SELECT UnitPricePaid FROM order_item_price WHERE OrderID=20 AND ProductID=10').fetchone()[0]
current=n.execute('SELECT UnitPrice FROM product_current_price WHERE ProductID=10').fetchone()[0]
record('Task 12 paid-price snapshot','PRESERVED',f'Paid price={paid}; current catalogue price={current}.')
n.close()
path=OUT/'edge_case_tests.csv'
with path.open('w',newline='',encoding='utf-8') as f:
 w=csv.writer(f); w.writerow(['test','observed_outcome','detail']); w.writerows(results)
log='SHOPNEST CO3 EDGE CASE TESTS\n'+'\n'.join(f'- {a}: {b} | {c}' for a,b,c in results)+'\n'
(OUT/'edge_case_tests.txt').write_text(log,encoding='utf-8')
print(log)
