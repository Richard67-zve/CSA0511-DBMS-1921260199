USE swiftspan_co2;

-- Read card is a rebuildable projection. BCNF tables remain the source of truth.
CREATE TABLE IF NOT EXISTS tracking_read_card (
  SenderID BIGINT NOT NULL,
  ServiceID INT NOT NULL,
  DispatchWave TINYINT NOT NULL,
  SenderName VARCHAR(100) NOT NULL,
  RouteGroup VARCHAR(20) NOT NULL,
  ServiceCode VARCHAR(20) NOT NULL,
  ServiceName VARCHAR(100) NOT NULL,
  VolumeWeight DECIMAL(8,3) NOT NULL,
  CoordinatorID INT NOT NULL,
  CoordinatorName VARCHAR(100) NOT NULL,
  Hub VARCHAR(50) NOT NULL,
  Completion TINYINT NOT NULL,
  ServiceBand VARCHAR(20) NOT NULL,
  RouteFactor DECIMAL(6,3) NOT NULL,
  AdjustedIndex DECIMAL(14,4) NOT NULL,
  PRIMARY KEY (SenderID, ServiceID, DispatchWave),
  KEY ix_read_card_sender_wave (SenderID, DispatchWave)
) ENGINE=InnoDB;

-- Run immediately after the six-hour reconciliation commit. The explicit
-- transaction makes delete + refill one atomic refresh to other transactions.
START TRANSACTION;
DELETE FROM tracking_read_card;
INSERT INTO tracking_read_card
SELECT s.SenderID, sv.ServiceID, o.DispatchWave, s.SenderName, s.RouteGroup,
       sv.ServiceCode, sv.ServiceName, sv.VolumeWeight,
       c.CoordinatorID, c.CoordinatorName, c.Hub, o.Completion,
       cp.ServiceBand, bp.RouteFactor,
       ROUND(o.Completion * sv.VolumeWeight * bp.RouteFactor, 4)
FROM bcnf_observation o
JOIN bcnf_sender s ON s.SenderID=o.SenderID
JOIN bcnf_service sv ON sv.ServiceID=o.ServiceID
JOIN bcnf_assignment a ON a.SenderID=o.SenderID AND a.ServiceID=o.ServiceID
JOIN bcnf_coordinator c ON c.CoordinatorID=a.CoordinatorID
JOIN bcnf_completion_policy cp ON cp.Completion=o.Completion
JOIN bcnf_service_band_policy bp ON bp.ServiceBand=cp.ServiceBand;
COMMIT;

-- Fast sender tracking read path (0 joins after refresh).
SELECT SenderID, ServiceID, ServiceCode, ServiceName, DispatchWave,
       Completion, ServiceBand, AdjustedIndex
FROM tracking_read_card
WHERE SenderID=? AND DispatchWave=?
ORDER BY ServiceID;
