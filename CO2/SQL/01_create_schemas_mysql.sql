-- CSA05 CO2 | SwiftSpan Parcels | MySQL 8.0.16+
-- Safe setup: creates a dedicated database; it does not drop existing objects.
CREATE DATABASE IF NOT EXISTS swiftspan_co2 CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE swiftspan_co2;

-- DESIGN 1: flat repeated-data baseline (all fourteen attributes).
CREATE TABLE IF NOT EXISTS flat_handover (
  SenderID BIGINT NOT NULL,
  SenderName VARCHAR(100) NOT NULL,
  RouteGroup VARCHAR(20) NOT NULL,
  ServiceID INT NOT NULL,
  ServiceCode VARCHAR(20) NOT NULL,
  ServiceName VARCHAR(100) NOT NULL,
  VolumeWeight DECIMAL(8,3) NOT NULL,
  DispatchWave TINYINT NOT NULL,
  CoordinatorID INT NOT NULL,
  CoordinatorName VARCHAR(100) NOT NULL,
  Hub VARCHAR(50) NOT NULL,
  Completion TINYINT NOT NULL,
  ServiceBand VARCHAR(20) NOT NULL,
  RouteFactor DECIMAL(6,3) NOT NULL,
  PRIMARY KEY (SenderID, ServiceID, DispatchWave),
  UNIQUE KEY uq_flat_alt_observation (SenderID, ServiceCode, DispatchWave),
  CONSTRAINT ck_flat_completion CHECK (Completion BETWEEN 0 AND 100),
  CONSTRAINT ck_flat_wave CHECK (DispatchWave BETWEEN 1 AND 4),
  CONSTRAINT ck_flat_weight CHECK (VolumeWeight > 0),
  CONSTRAINT ck_flat_factor CHECK (RouteFactor > 0),
  KEY ix_flat_sender_wave (SenderID, DispatchWave),
  KEY ix_flat_service_wave (ServiceID, DispatchWave)
) ENGINE=InnoDB;

-- DESIGN 2: partial decomposition. Sender and service identity/catalog facts
-- are removed from the repeated observation row. Assignment/operator and policy
-- consequences intentionally remain redundant in partial_observation.
CREATE TABLE IF NOT EXISTS partial_sender (
  SenderID BIGINT PRIMARY KEY,
  SenderName VARCHAR(100) NOT NULL,
  RouteGroup VARCHAR(20) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS partial_service (
  ServiceID INT PRIMARY KEY,
  ServiceCode VARCHAR(20) NOT NULL UNIQUE,
  ServiceName VARCHAR(100) NOT NULL,
  VolumeWeight DECIMAL(8,3) NOT NULL CHECK (VolumeWeight > 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS partial_observation (
  SenderID BIGINT NOT NULL,
  ServiceID INT NOT NULL,
  DispatchWave TINYINT NOT NULL,
  CoordinatorID INT NOT NULL,
  CoordinatorName VARCHAR(100) NOT NULL,
  Hub VARCHAR(50) NOT NULL,
  Completion TINYINT NOT NULL,
  ServiceBand VARCHAR(20) NOT NULL,
  RouteFactor DECIMAL(6,3) NOT NULL,
  PRIMARY KEY (SenderID, ServiceID, DispatchWave),
  CONSTRAINT fk_partial_sender FOREIGN KEY (SenderID) REFERENCES partial_sender(SenderID) ON DELETE RESTRICT,
  CONSTRAINT fk_partial_service FOREIGN KEY (ServiceID) REFERENCES partial_service(ServiceID) ON DELETE RESTRICT,
  CONSTRAINT ck_partial_completion CHECK (Completion BETWEEN 0 AND 100),
  CONSTRAINT ck_partial_wave CHECK (DispatchWave BETWEEN 1 AND 4),
  KEY ix_partial_sender_wave (SenderID, DispatchWave),
  KEY ix_partial_service_wave (ServiceID, DispatchWave)
) ENGINE=InnoDB;

-- DESIGN 3: BCNF source-of-truth schema.
CREATE TABLE IF NOT EXISTS bcnf_sender (
  SenderID BIGINT PRIMARY KEY,
  SenderName VARCHAR(100) NOT NULL,
  RouteGroup VARCHAR(20) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bcnf_service (
  ServiceID INT PRIMARY KEY,
  ServiceCode VARCHAR(20) NOT NULL UNIQUE,
  ServiceName VARCHAR(100) NOT NULL,
  VolumeWeight DECIMAL(8,3) NOT NULL CHECK (VolumeWeight > 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bcnf_coordinator (
  CoordinatorID INT PRIMARY KEY,
  CoordinatorName VARCHAR(100) NOT NULL,
  Hub VARCHAR(50) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bcnf_assignment (
  SenderID BIGINT NOT NULL,
  ServiceID INT NOT NULL,
  CoordinatorID INT NOT NULL,
  PRIMARY KEY (SenderID, ServiceID),
  CONSTRAINT fk_assignment_sender FOREIGN KEY (SenderID) REFERENCES bcnf_sender(SenderID) ON DELETE RESTRICT,
  CONSTRAINT fk_assignment_service FOREIGN KEY (ServiceID) REFERENCES bcnf_service(ServiceID) ON DELETE RESTRICT,
  CONSTRAINT fk_assignment_coord FOREIGN KEY (CoordinatorID) REFERENCES bcnf_coordinator(CoordinatorID) ON DELETE RESTRICT,
  KEY ix_assignment_coord (CoordinatorID)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bcnf_observation (
  SenderID BIGINT NOT NULL,
  ServiceID INT NOT NULL,
  DispatchWave TINYINT NOT NULL,
  Completion TINYINT NOT NULL,
  PRIMARY KEY (SenderID, ServiceID, DispatchWave),
  CONSTRAINT fk_observation_assignment FOREIGN KEY (SenderID, ServiceID)
    REFERENCES bcnf_assignment(SenderID, ServiceID) ON DELETE RESTRICT,
  CONSTRAINT ck_bcnf_completion CHECK (Completion BETWEEN 0 AND 100),
  CONSTRAINT ck_bcnf_wave CHECK (DispatchWave BETWEEN 1 AND 4),
  KEY ix_observation_sender_wave (SenderID, DispatchWave),
  KEY ix_observation_service_wave_completion (ServiceID, DispatchWave, Completion)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bcnf_service_band_policy (
  ServiceBand VARCHAR(20) PRIMARY KEY,
  RouteFactor DECIMAL(6,3) NOT NULL CHECK (RouteFactor > 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bcnf_completion_policy (
  Completion TINYINT PRIMARY KEY,
  ServiceBand VARCHAR(20) NOT NULL,
  CONSTRAINT ck_policy_completion CHECK (Completion BETWEEN 0 AND 100),
  CONSTRAINT fk_completion_band FOREIGN KEY (ServiceBand)
    REFERENCES bcnf_service_band_policy(ServiceBand) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Auxiliary requirement mapping for universal quantification in Task 7.
CREATE TABLE IF NOT EXISTS bcnf_group_required_service (
  RouteGroup VARCHAR(20) NOT NULL,
  ServiceID INT NOT NULL,
  PRIMARY KEY (RouteGroup, ServiceID),
  CONSTRAINT fk_group_service FOREIGN KEY (ServiceID) REFERENCES bcnf_service(ServiceID) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dispatch_wave (
  WaveValue TINYINT PRIMARY KEY CHECK (WaveValue BETWEEN 1 AND 4)
) ENGINE=InnoDB;

INSERT IGNORE INTO dispatch_wave VALUES (1),(2),(3),(4);

-- Policy is explicit and deterministic: 0-38 LOW, 39-69 STANDARD, 70-100 HIGH.
INSERT IGNORE INTO bcnf_service_band_policy VALUES ('LOW',1.250),('STANDARD',1.000),('HIGH',0.850);
INSERT IGNORE INTO bcnf_completion_policy (Completion, ServiceBand) VALUES
(0,'LOW'),(1,'LOW'),(2,'LOW'),(3,'LOW'),(4,'LOW'),(5,'LOW'),(6,'LOW'),(7,'LOW'),(8,'LOW'),(9,'LOW'),
(10,'LOW'),(11,'LOW'),(12,'LOW'),(13,'LOW'),(14,'LOW'),(15,'LOW'),(16,'LOW'),(17,'LOW'),(18,'LOW'),(19,'LOW'),
(20,'LOW'),(21,'LOW'),(22,'LOW'),(23,'LOW'),(24,'LOW'),(25,'LOW'),(26,'LOW'),(27,'LOW'),(28,'LOW'),(29,'LOW'),
(30,'LOW'),(31,'LOW'),(32,'LOW'),(33,'LOW'),(34,'LOW'),(35,'LOW'),(36,'LOW'),(37,'LOW'),(38,'LOW'),
(39,'STANDARD'),(40,'STANDARD'),(41,'STANDARD'),(42,'STANDARD'),(43,'STANDARD'),(44,'STANDARD'),(45,'STANDARD'),(46,'STANDARD'),(47,'STANDARD'),(48,'STANDARD'),
(49,'STANDARD'),(50,'STANDARD'),(51,'STANDARD'),(52,'STANDARD'),(53,'STANDARD'),(54,'STANDARD'),(55,'STANDARD'),(56,'STANDARD'),(57,'STANDARD'),(58,'STANDARD'),
(59,'STANDARD'),(60,'STANDARD'),(61,'STANDARD'),(62,'STANDARD'),(63,'STANDARD'),(64,'STANDARD'),(65,'STANDARD'),(66,'STANDARD'),(67,'STANDARD'),(68,'STANDARD'),(69,'STANDARD'),
(70,'HIGH'),(71,'HIGH'),(72,'HIGH'),(73,'HIGH'),(74,'HIGH'),(75,'HIGH'),(76,'HIGH'),(77,'HIGH'),(78,'HIGH'),(79,'HIGH'),
(80,'HIGH'),(81,'HIGH'),(82,'HIGH'),(83,'HIGH'),(84,'HIGH'),(85,'HIGH'),(86,'HIGH'),(87,'HIGH'),(88,'HIGH'),(89,'HIGH'),
(90,'HIGH'),(91,'HIGH'),(92,'HIGH'),(93,'HIGH'),(94,'HIGH'),(95,'HIGH'),(96,'HIGH'),(97,'HIGH'),(98,'HIGH'),(99,'HIGH'),(100,'HIGH');
