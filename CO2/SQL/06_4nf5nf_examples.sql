-- Task 6 conceptual SQL examples; execute separately in MySQL.
USE swiftspan_co2;
CREATE TABLE IF NOT EXISTS service_mode (
  ServiceID INT NOT NULL,
  TransportMode VARCHAR(30) NOT NULL,
  PRIMARY KEY(ServiceID, TransportMode),
  FOREIGN KEY(ServiceID) REFERENCES bcnf_service(ServiceID) ON DELETE RESTRICT
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS service_document (
  ServiceID INT NOT NULL,
  DocumentType VARCHAR(40) NOT NULL,
  PRIMARY KEY(ServiceID, DocumentType),
  FOREIGN KEY(ServiceID) REFERENCES bcnf_service(ServiceID) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Three-way authorization rule: an authorization triple is valid iff all three
-- pairwise approvals exist. The join reconstructs the valid triple relation.
CREATE TABLE IF NOT EXISTS operator_item_approval (
  OperatorID VARCHAR(30) NOT NULL, ItemID VARCHAR(30) NOT NULL,
  PRIMARY KEY(OperatorID, ItemID)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS operator_channel_approval (
  OperatorID VARCHAR(30) NOT NULL, ChannelID VARCHAR(30) NOT NULL,
  PRIMARY KEY(OperatorID, ChannelID)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS item_channel_approval (
  ItemID VARCHAR(30) NOT NULL, ChannelID VARCHAR(30) NOT NULL,
  PRIMARY KEY(ItemID, ChannelID)
) ENGINE=InnoDB;

SELECT oi.OperatorID, oi.ItemID, oc.ChannelID
FROM operator_item_approval oi
JOIN operator_channel_approval oc USING(OperatorID)
JOIN item_channel_approval ic
  ON ic.ItemID=oi.ItemID AND ic.ChannelID=oc.ChannelID;
