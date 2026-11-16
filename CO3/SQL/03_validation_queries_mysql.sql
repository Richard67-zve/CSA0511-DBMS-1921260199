USE shopnest_co3;
-- 1. Complete order history for one customer.
SELECT o.OrderID,o.OrderDate,c.CustomerName,p.ProductName,oi.Quantity,s.SupplierName
FROM orders_4nf o
JOIN customer_4nf c ON c.CustomerID=o.CustomerID
JOIN order_item_4nf oi ON oi.OrderID=o.OrderID
JOIN product_4nf p ON p.ProductID=oi.ProductID
JOIN supplier_4nf s ON s.SupplierID=p.SupplierID
WHERE o.CustomerID=? ORDER BY o.OrderDate DESC,o.OrderID;

-- 2. Total quantity and value by order (uses the stored paid price after Task 12).
SELECT oi.OrderID,SUM(oi.Quantity) AS total_units,
       SUM(oi.Quantity*oi.UnitPricePaid) AS paid_total
FROM order_item_4nf oi GROUP BY oi.OrderID;

-- 3. Products never ordered.
SELECT p.ProductID,p.ProductName
FROM product_4nf p
LEFT JOIN order_item_4nf oi ON oi.ProductID=p.ProductID
WHERE oi.ProductID IS NULL;

-- 4. Products with all tags and all colours are stored independently.
SELECT p.ProductID,COUNT(DISTINCT t.Tag) AS tag_count,COUNT(DISTINCT c.Colour) AS colour_count
FROM product_4nf p
LEFT JOIN product_tag_4nf t ON t.ProductID=p.ProductID
LEFT JOIN product_colour_4nf c ON c.ProductID=p.ProductID
GROUP BY p.ProductID;

-- 5. 5NF reconstructed supply triples from the three pair relations.
SELECT sc.SupplierID,sc.CategoryID,cw.WarehouseID
FROM supply_supplier_category_5nf sc
JOIN supply_category_warehouse_5nf cw ON cw.CategoryID=sc.CategoryID
JOIN supply_supplier_warehouse_5nf sw ON sw.SupplierID=sc.SupplierID AND sw.WarehouseID=cw.WarehouseID;

-- 6. Price-history current row.
SELECT ProductID,UnitPrice FROM product_price_history WHERE ProductID=? AND ValidTo IS NULL;

-- 7. Query plan for the frequently used order-history path.
EXPLAIN SELECT oi.OrderID,oi.ProductID,oi.UnitPricePaid
FROM order_item_4nf oi WHERE oi.OrderID=?;

-- 8. Constraint trials: run one at a time and expect a duplicate/foreign-key/CHECK error.
-- INSERT INTO order_item_4nf(OrderID,ProductID,Quantity,UnitPricePaid,WarehouseID) VALUES(1,1,0,10,1);
-- INSERT INTO order_item_4nf(OrderID,ProductID,Quantity,UnitPricePaid,WarehouseID) VALUES(1,999999,1,10,1);
