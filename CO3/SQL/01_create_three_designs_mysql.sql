-- ShopNest CO3 - MySQL 8.0 schema definitions
-- Execute this script in MySQL Workbench or MySQL Command Line Client.
CREATE DATABASE IF NOT EXISTS shopnest_co3;
USE shopnest_co3;

-- DESIGN A: Unnormalised 1NF demonstration baseline (TagList/ColourList remain lists).
DROP TABLE IF EXISTS order_line_unf;
CREATE TABLE order_line_unf (
  OrderID BIGINT NOT NULL, OrderDate DATE NOT NULL,
  CustomerID BIGINT NOT NULL, CustomerName VARCHAR(100) NOT NULL,
  CustomerEmail VARCHAR(160) NOT NULL,
  ShipStreet VARCHAR(160) NOT NULL, ShipCity VARCHAR(80) NOT NULL,
  ShipPIN VARCHAR(12) NOT NULL, ShipState VARCHAR(80) NOT NULL,
  ProductID BIGINT NOT NULL, ProductName VARCHAR(160) NOT NULL,
  UnitPrice DECIMAL(12,2) NOT NULL,
  CategoryID BIGINT NOT NULL, CategoryName VARCHAR(100) NOT NULL,
  SupplierID BIGINT NOT NULL, SupplierName VARCHAR(120) NOT NULL,
  SupplierPhone VARCHAR(32) NOT NULL,
  Quantity INT NOT NULL CHECK (Quantity > 0),
  WarehouseID BIGINT NOT NULL, WarehouseCity VARCHAR(100) NOT NULL,
  TagList VARCHAR(500) NOT NULL, ColourList VARCHAR(300) NOT NULL,
  PRIMARY KEY (OrderID, ProductID),
  KEY ix_unf_supplier (SupplierID),
  KEY ix_unf_order_date (OrderDate, OrderID)
) ENGINE=InnoDB;

-- DESIGN B: 3NF relations. Address retains the 3NF determinant pair
-- (ShipStreet, ShipCity) -> ShipPIN; all address attributes are prime in that relation.
DROP TABLE IF EXISTS product_tag_colour_3nf;
DROP TABLE IF EXISTS order_item_3nf;
DROP TABLE IF EXISTS orders_3nf;
DROP TABLE IF EXISTS shipping_address_3nf;
DROP TABLE IF EXISTS postal_state_3nf;
DROP TABLE IF EXISTS product_3nf;
DROP TABLE IF EXISTS supplier_3nf;
DROP TABLE IF EXISTS category_3nf;
DROP TABLE IF EXISTS warehouse_3nf;
DROP TABLE IF EXISTS customer_3nf;
CREATE TABLE customer_3nf (
  CustomerID BIGINT PRIMARY KEY, CustomerName VARCHAR(100) NOT NULL,
  CustomerEmail VARCHAR(160) NOT NULL UNIQUE
) ENGINE=InnoDB;
CREATE TABLE supplier_3nf (
  SupplierID BIGINT PRIMARY KEY, SupplierName VARCHAR(120) NOT NULL,
  SupplierPhone VARCHAR(32) NOT NULL
) ENGINE=InnoDB;
CREATE TABLE category_3nf (
  CategoryID BIGINT PRIMARY KEY, CategoryName VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;
CREATE TABLE warehouse_3nf (
  WarehouseID BIGINT PRIMARY KEY, WarehouseCity VARCHAR(100) NOT NULL
) ENGINE=InnoDB;
CREATE TABLE product_3nf (
  ProductID BIGINT PRIMARY KEY, ProductName VARCHAR(160) NOT NULL,
  CurrentUnitPrice DECIMAL(12,2) NOT NULL CHECK (CurrentUnitPrice >= 0),
  CategoryID BIGINT NOT NULL, SupplierID BIGINT NOT NULL,
  CONSTRAINT fk_p3_cat FOREIGN KEY (CategoryID) REFERENCES category_3nf(CategoryID) ON DELETE RESTRICT,
  CONSTRAINT fk_p3_sup FOREIGN KEY (SupplierID) REFERENCES supplier_3nf(SupplierID) ON DELETE RESTRICT
) ENGINE=InnoDB;
CREATE TABLE postal_state_3nf (
  ShipPIN VARCHAR(12) PRIMARY KEY, ShipState VARCHAR(80) NOT NULL
) ENGINE=InnoDB;
CREATE TABLE shipping_address_3nf (
  AddressID BIGINT AUTO_INCREMENT PRIMARY KEY,
  ShipStreet VARCHAR(160) NOT NULL, ShipCity VARCHAR(80) NOT NULL,
  ShipPIN VARCHAR(12) NOT NULL,
  UNIQUE KEY uq_addr_street_city (ShipStreet, ShipCity),
  UNIQUE KEY uq_addr_street_pin (ShipStreet, ShipPIN),
  FOREIGN KEY (ShipPIN) REFERENCES postal_state_3nf(ShipPIN) ON DELETE RESTRICT
) ENGINE=InnoDB;
CREATE TABLE orders_3nf (
  OrderID BIGINT PRIMARY KEY, OrderDate DATE NOT NULL,
  CustomerID BIGINT NOT NULL, AddressID BIGINT NOT NULL,
  FOREIGN KEY (CustomerID) REFERENCES customer_3nf(CustomerID) ON DELETE RESTRICT,
  FOREIGN KEY (AddressID) REFERENCES shipping_address_3nf(AddressID) ON DELETE RESTRICT,
  KEY ix_o3_customer_date (CustomerID, OrderDate)
) ENGINE=InnoDB;
CREATE TABLE order_item_3nf (
  OrderID BIGINT NOT NULL, ProductID BIGINT NOT NULL,
  Quantity INT NOT NULL CHECK (Quantity > 0), WarehouseID BIGINT NOT NULL,
  PRIMARY KEY (OrderID, ProductID),
  FOREIGN KEY (OrderID) REFERENCES orders_3nf(OrderID) ON DELETE RESTRICT,
  FOREIGN KEY (ProductID) REFERENCES product_3nf(ProductID) ON DELETE RESTRICT,
  FOREIGN KEY (WarehouseID) REFERENCES warehouse_3nf(WarehouseID) ON DELETE RESTRICT,
  KEY ix_oi3_product (ProductID, OrderID)
) ENGINE=InnoDB;
CREATE TABLE product_tag_colour_3nf (
  ProductID BIGINT NOT NULL, Tag VARCHAR(80) NOT NULL, Colour VARCHAR(60) NOT NULL,
  PRIMARY KEY (ProductID, Tag, Colour),
  FOREIGN KEY (ProductID) REFERENCES product_3nf(ProductID) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- DESIGN C: BCNF / 4NF / 5NF relations.
DROP TABLE IF EXISTS supply_supplier_warehouse_5nf;
DROP TABLE IF EXISTS supply_category_warehouse_5nf;
DROP TABLE IF EXISTS supply_supplier_category_5nf;
DROP TABLE IF EXISTS product_colour_4nf;
DROP TABLE IF EXISTS product_tag_4nf;
DROP TABLE IF EXISTS order_item_4nf;
DROP TABLE IF EXISTS orders_4nf;
DROP TABLE IF EXISTS shipping_address_4nf;
DROP TABLE IF EXISTS postal_area_4nf;
DROP TABLE IF EXISTS product_4nf;
DROP TABLE IF EXISTS supplier_4nf;
DROP TABLE IF EXISTS category_4nf;
DROP TABLE IF EXISTS warehouse_4nf;
DROP TABLE IF EXISTS customer_4nf;
CREATE TABLE customer_4nf LIKE customer_3nf;
CREATE TABLE supplier_4nf LIKE supplier_3nf;
CREATE TABLE category_4nf LIKE category_3nf;
CREATE TABLE warehouse_4nf LIKE warehouse_3nf;
CREATE TABLE product_4nf LIKE product_3nf;
CREATE TABLE postal_area_4nf (
  ShipPIN VARCHAR(12) PRIMARY KEY, ShipCity VARCHAR(80) NOT NULL, ShipState VARCHAR(80) NOT NULL
) ENGINE=InnoDB;
CREATE TABLE shipping_address_4nf (
  ShipStreet VARCHAR(160) NOT NULL, ShipPIN VARCHAR(12) NOT NULL,
  PRIMARY KEY (ShipStreet, ShipPIN),
  FOREIGN KEY (ShipPIN) REFERENCES postal_area_4nf(ShipPIN) ON DELETE RESTRICT
) ENGINE=InnoDB;
CREATE TABLE orders_4nf (
  OrderID BIGINT PRIMARY KEY, OrderDate DATE NOT NULL, CustomerID BIGINT NOT NULL,
  ShipStreet VARCHAR(160) NOT NULL, ShipPIN VARCHAR(12) NOT NULL,
  FOREIGN KEY (CustomerID) REFERENCES customer_4nf(CustomerID) ON DELETE RESTRICT,
  FOREIGN KEY (ShipStreet,ShipPIN) REFERENCES shipping_address_4nf(ShipStreet,ShipPIN) ON DELETE RESTRICT,
  KEY ix_o4_customer_date (CustomerID,OrderDate)
) ENGINE=InnoDB;
CREATE TABLE order_item_4nf (
  OrderID BIGINT NOT NULL, ProductID BIGINT NOT NULL, Quantity INT NOT NULL CHECK (Quantity>0), WarehouseID BIGINT NOT NULL,
  PRIMARY KEY (OrderID,ProductID),
  FOREIGN KEY (OrderID) REFERENCES orders_4nf(OrderID) ON DELETE RESTRICT,
  FOREIGN KEY (ProductID) REFERENCES product_4nf(ProductID) ON DELETE RESTRICT,
  FOREIGN KEY (WarehouseID) REFERENCES warehouse_4nf(WarehouseID) ON DELETE RESTRICT,
  KEY ix_oi4_product (ProductID,OrderID)
) ENGINE=InnoDB;
CREATE TABLE product_tag_4nf (
  ProductID BIGINT NOT NULL, Tag VARCHAR(80) NOT NULL,
  PRIMARY KEY (ProductID,Tag), FOREIGN KEY (ProductID) REFERENCES product_4nf(ProductID) ON DELETE RESTRICT
) ENGINE=InnoDB;
CREATE TABLE product_colour_4nf (
  ProductID BIGINT NOT NULL, Colour VARCHAR(60) NOT NULL,
  PRIMARY KEY (ProductID,Colour), FOREIGN KEY (ProductID) REFERENCES product_4nf(ProductID) ON DELETE RESTRICT
) ENGINE=InnoDB;
CREATE TABLE supply_supplier_category_5nf (SupplierID BIGINT NOT NULL, CategoryID BIGINT NOT NULL, PRIMARY KEY(SupplierID,CategoryID)) ENGINE=InnoDB;
CREATE TABLE supply_category_warehouse_5nf (CategoryID BIGINT NOT NULL, WarehouseID BIGINT NOT NULL, PRIMARY KEY(CategoryID,WarehouseID)) ENGINE=InnoDB;
CREATE TABLE supply_supplier_warehouse_5nf (SupplierID BIGINT NOT NULL, WarehouseID BIGINT NOT NULL, PRIMARY KEY(SupplierID,WarehouseID)) ENGINE=InnoDB;

-- Cross-row determinant checks for the unnormalised comparison table.
-- In practice these checks are expensive; they illustrate the extra enforcement
-- needed when the same determinant is repeated across many observation rows.
DROP TRIGGER IF EXISTS trg_unf_fd_bi;
DELIMITER $$
CREATE TRIGGER trg_unf_fd_bi BEFORE INSERT ON order_line_unf FOR EACH ROW
BEGIN
  IF EXISTS (SELECT 1 FROM order_line_unf x WHERE x.CustomerID=NEW.CustomerID
       AND (x.CustomerName<>NEW.CustomerName OR x.CustomerEmail<>NEW.CustomerEmail)) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: CustomerID determines customer details';
  END IF;
  IF EXISTS (SELECT 1 FROM order_line_unf x WHERE x.ProductID=NEW.ProductID
       AND (x.ProductName<>NEW.ProductName OR x.UnitPrice<>NEW.UnitPrice OR x.TagList<>NEW.TagList OR x.ColourList<>NEW.ColourList OR x.CategoryID<>NEW.CategoryID OR x.SupplierID<>NEW.SupplierID)) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: ProductID determines product details';
  END IF;
  IF EXISTS (SELECT 1 FROM order_line_unf x WHERE x.SupplierID=NEW.SupplierID
       AND (x.SupplierName<>NEW.SupplierName OR x.SupplierPhone<>NEW.SupplierPhone)) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: SupplierID determines supplier details';
  END IF;
  IF EXISTS (SELECT 1 FROM order_line_unf x WHERE x.OrderID=NEW.OrderID
       AND (x.OrderDate<>NEW.OrderDate OR x.CustomerID<>NEW.CustomerID OR x.ShipStreet<>NEW.ShipStreet OR x.ShipPIN<>NEW.ShipPIN)) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: OrderID determines order header facts';
  END IF;
  IF EXISTS (SELECT 1 FROM order_line_unf x WHERE x.CategoryID=NEW.CategoryID AND x.CategoryName<>NEW.CategoryName) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: CategoryID determines CategoryName';
  END IF;
  IF EXISTS (SELECT 1 FROM order_line_unf x WHERE x.WarehouseID=NEW.WarehouseID AND x.WarehouseCity<>NEW.WarehouseCity) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: WarehouseID determines WarehouseCity';
  END IF;
  IF EXISTS (SELECT 1 FROM order_line_unf x WHERE x.ShipPIN=NEW.ShipPIN AND (x.ShipCity<>NEW.ShipCity OR x.ShipState<>NEW.ShipState)) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: ShipPIN determines city and state';
  END IF;
  IF EXISTS (SELECT 1 FROM order_line_unf x WHERE x.ShipStreet=NEW.ShipStreet AND x.ShipCity=NEW.ShipCity AND x.ShipPIN<>NEW.ShipPIN) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: street and city determine PIN';
  END IF;
END$$
DELIMITER ;

-- Add the foreign keys omitted by MySQL CREATE TABLE ... LIKE above.
ALTER TABLE product_4nf
  ADD CONSTRAINT fk_p4_cat FOREIGN KEY (CategoryID) REFERENCES category_4nf(CategoryID) ON DELETE RESTRICT,
  ADD CONSTRAINT fk_p4_sup FOREIGN KEY (SupplierID) REFERENCES supplier_4nf(SupplierID) ON DELETE RESTRICT;

-- Update-side FD guard (exclude the row being updated from the comparisons).
DROP TRIGGER IF EXISTS trg_unf_fd_bu;
DELIMITER $$
CREATE TRIGGER trg_unf_fd_bu BEFORE UPDATE ON order_line_unf FOR EACH ROW
BEGIN
  IF EXISTS (SELECT 1 FROM order_line_unf x WHERE NOT (x.OrderID=OLD.OrderID AND x.ProductID=OLD.ProductID) AND x.CustomerID=NEW.CustomerID AND (x.CustomerName<>NEW.CustomerName OR x.CustomerEmail<>NEW.CustomerEmail)) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: CustomerID determines customer details';
  END IF;
  IF EXISTS (SELECT 1 FROM order_line_unf x WHERE NOT (x.OrderID=OLD.OrderID AND x.ProductID=OLD.ProductID) AND x.ProductID=NEW.ProductID AND (x.ProductName<>NEW.ProductName OR x.UnitPrice<>NEW.UnitPrice OR x.TagList<>NEW.TagList OR x.ColourList<>NEW.ColourList OR x.CategoryID<>NEW.CategoryID OR x.SupplierID<>NEW.SupplierID)) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: ProductID determines product details';
  END IF;
  IF EXISTS (SELECT 1 FROM order_line_unf x WHERE NOT (x.OrderID=OLD.OrderID AND x.ProductID=OLD.ProductID) AND x.SupplierID=NEW.SupplierID AND (x.SupplierName<>NEW.SupplierName OR x.SupplierPhone<>NEW.SupplierPhone)) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: SupplierID determines supplier details';
  END IF;
  IF EXISTS (SELECT 1 FROM order_line_unf x WHERE NOT (x.OrderID=OLD.OrderID AND x.ProductID=OLD.ProductID) AND x.OrderID=NEW.OrderID AND (x.OrderDate<>NEW.OrderDate OR x.CustomerID<>NEW.CustomerID OR x.ShipStreet<>NEW.ShipStreet OR x.ShipPIN<>NEW.ShipPIN)) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: OrderID determines order header facts';
  END IF;
  IF EXISTS (SELECT 1 FROM order_line_unf x WHERE NOT (x.OrderID=OLD.OrderID AND x.ProductID=OLD.ProductID) AND x.CategoryID=NEW.CategoryID AND x.CategoryName<>NEW.CategoryName) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: CategoryID determines CategoryName';
  END IF;
  IF EXISTS (SELECT 1 FROM order_line_unf x WHERE NOT (x.OrderID=OLD.OrderID AND x.ProductID=OLD.ProductID) AND x.WarehouseID=NEW.WarehouseID AND x.WarehouseCity<>NEW.WarehouseCity) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: WarehouseID determines WarehouseCity';
  END IF;
  IF EXISTS (SELECT 1 FROM order_line_unf x WHERE NOT (x.OrderID=OLD.OrderID AND x.ProductID=OLD.ProductID) AND x.ShipPIN=NEW.ShipPIN AND (x.ShipCity<>NEW.ShipCity OR x.ShipState<>NEW.ShipState)) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: ShipPIN determines city and state';
  END IF;
  IF EXISTS (SELECT 1 FROM order_line_unf x WHERE NOT (x.OrderID=OLD.OrderID AND x.ProductID=OLD.ProductID) AND x.ShipStreet=NEW.ShipStreet AND x.ShipCity=NEW.ShipCity AND x.ShipPIN<>NEW.ShipPIN) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: street and city determine PIN';
  END IF;
END$$
DELIMITER ;

-- Guard the 4NF address decomposition: ShipStreet + the city obtained from its PIN
-- must continue to determine the same PIN across stored address pairs.
DROP TRIGGER IF EXISTS trg_address4nf_bi;
DELIMITER $$
CREATE TRIGGER trg_address4nf_bi BEFORE INSERT ON shipping_address_4nf FOR EACH ROW
BEGIN
  IF EXISTS (
    SELECT 1 FROM shipping_address_4nf a
    JOIN postal_area_4nf p_old ON p_old.ShipPIN=a.ShipPIN
    JOIN postal_area_4nf p_new ON p_new.ShipPIN=NEW.ShipPIN
    WHERE a.ShipStreet=NEW.ShipStreet AND p_old.ShipCity=p_new.ShipCity AND a.ShipPIN<>NEW.ShipPIN
  ) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: ShipStreet and ShipCity determine ShipPIN';
  END IF;
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS trg_address4nf_bu;
DELIMITER $$
CREATE TRIGGER trg_address4nf_bu BEFORE UPDATE ON shipping_address_4nf FOR EACH ROW
BEGIN
  IF EXISTS (
    SELECT 1 FROM shipping_address_4nf a
    JOIN postal_area_4nf p_old ON p_old.ShipPIN=a.ShipPIN
    JOIN postal_area_4nf p_new ON p_new.ShipPIN=NEW.ShipPIN
    WHERE NOT (a.ShipStreet=OLD.ShipStreet AND a.ShipPIN=OLD.ShipPIN)
      AND a.ShipStreet=NEW.ShipStreet AND p_old.ShipCity=p_new.ShipCity AND a.ShipPIN<>NEW.ShipPIN
  ) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: ShipStreet and ShipCity determine ShipPIN';
  END IF;
END$$
DELIMITER ;

-- Guard the 3NF address relation's PIN -> city rule, which is retained by
-- keeping ShipCity and ShipPIN together in the address relation.
DROP TRIGGER IF EXISTS trg_address3nf_bi;
DELIMITER $$
CREATE TRIGGER trg_address3nf_bi BEFORE INSERT ON shipping_address_3nf FOR EACH ROW
BEGIN
  IF EXISTS (SELECT 1 FROM shipping_address_3nf a WHERE a.ShipPIN=NEW.ShipPIN AND a.ShipCity<>NEW.ShipCity) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: ShipPIN determines ShipCity';
  END IF;
END$$
DELIMITER ;
DROP TRIGGER IF EXISTS trg_address3nf_bu;
DELIMITER $$
CREATE TRIGGER trg_address3nf_bu BEFORE UPDATE ON shipping_address_3nf FOR EACH ROW
BEGIN
  IF EXISTS (SELECT 1 FROM shipping_address_3nf a WHERE a.AddressID<>OLD.AddressID AND a.ShipPIN=NEW.ShipPIN AND a.ShipCity<>NEW.ShipCity) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='FD violation: ShipPIN determines ShipCity';
  END IF;
END$$
DELIMITER ;

