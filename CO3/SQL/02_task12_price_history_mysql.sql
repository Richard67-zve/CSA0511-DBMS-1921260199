-- Task 12: preserve the price actually paid and the price history.
USE shopnest_co3;

-- Keep the source schema normalised. Historical paid prices are a line-level
-- transaction fact; do not derive them later from the current product price.
-- Add as NULL first because the exact historical prices must come from invoice /
-- payment records. Do NOT silently backfill old orders from current catalogue price.
ALTER TABLE order_item_4nf
  ADD COLUMN UnitPricePaid DECIMAL(12,2) NULL AFTER Quantity;

-- Staging table for verified invoice/order-line history supplied by the store.
-- Import (OrderID, ProductID, UnitPricePaid) from the historical invoice source.
CREATE TABLE IF NOT EXISTS order_item_paid_price_stage (
  OrderID BIGINT NOT NULL,
  ProductID BIGINT NOT NULL,
  UnitPricePaid DECIMAL(12,2) NOT NULL CHECK (UnitPricePaid >= 0),
  PRIMARY KEY (OrderID, ProductID),
  FOREIGN KEY (OrderID, ProductID)
    REFERENCES order_item_4nf(OrderID, ProductID) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Apply verified historical paid prices to existing order lines.
UPDATE order_item_4nf oi
JOIN order_item_paid_price_stage st
  ON st.OrderID = oi.OrderID AND st.ProductID = oi.ProductID
SET oi.UnitPricePaid = st.UnitPricePaid;

-- Check for historical rows still missing a verified price.
SELECT COUNT(*) AS lines_missing_verified_paid_price
FROM order_item_4nf
WHERE UnitPricePaid IS NULL;

-- Run the following only after the result above is zero:
-- ALTER TABLE order_item_4nf
--   MODIFY COLUMN UnitPricePaid DECIMAL(12,2) NOT NULL;
-- The staging table can then be archived or dropped according to the audit policy.

-- Temporal catalogue price history. Application transactions must close the
-- previous ValidTo and insert the new current row atomically; overlap validation
-- must be performed by the transaction/service or a dedicated trigger.
CREATE TABLE IF NOT EXISTS product_price_history (
  ProductID BIGINT NOT NULL,
  ValidFrom DATETIME NOT NULL,
  ValidTo DATETIME NULL,
  UnitPrice DECIMAL(12,2) NOT NULL CHECK (UnitPrice >= 0),
  PRIMARY KEY (ProductID, ValidFrom),
  FOREIGN KEY (ProductID) REFERENCES product_4nf(ProductID) ON DELETE RESTRICT,
  CHECK (ValidTo IS NULL OR ValidTo > ValidFrom),
  KEY ix_price_current (ProductID, ValidTo, ValidFrom)
) ENGINE=InnoDB;

-- Indexed order-history access path for frequent lookup workloads.
CREATE INDEX ix_order_history
  ON order_item_4nf(OrderID, ProductID, UnitPricePaid);
