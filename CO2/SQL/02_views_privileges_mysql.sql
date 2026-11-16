USE swiftspan_co2;

CREATE OR REPLACE VIEW v_sender_tracking AS
SELECT s.SenderID, s.SenderName, s.RouteGroup, sv.ServiceID, sv.ServiceCode,
       sv.ServiceName, o.DispatchWave, o.Completion, cp.ServiceBand, bp.RouteFactor,
       ROUND(o.Completion * sv.VolumeWeight * bp.RouteFactor, 4) AS AdjustedIndex
FROM bcnf_observation o
JOIN bcnf_sender s ON s.SenderID=o.SenderID
JOIN bcnf_service sv ON sv.ServiceID=o.ServiceID
JOIN bcnf_assignment a ON a.SenderID=o.SenderID AND a.ServiceID=o.ServiceID
JOIN bcnf_coordinator c ON c.CoordinatorID=a.CoordinatorID
JOIN bcnf_completion_policy cp ON cp.Completion=o.Completion
JOIN bcnf_service_band_policy bp ON bp.ServiceBand=cp.ServiceBand;

CREATE OR REPLACE VIEW v_coordinator_workload AS
SELECT c.CoordinatorID, c.CoordinatorName, c.Hub,
       COUNT(*) AS ObservationCount, AVG(o.Completion) AS MeanCompletion
FROM bcnf_observation o
JOIN bcnf_assignment a ON a.SenderID=o.SenderID AND a.ServiceID=o.ServiceID
JOIN bcnf_coordinator c ON c.CoordinatorID=a.CoordinatorID
GROUP BY c.CoordinatorID, c.CoordinatorName, c.Hub;

-- Privilege examples only. Replace the account/host with an approved campus account.
-- CREATE ROLE IF NOT EXISTS 'tracking_reader';
-- GRANT SELECT ON swiftspan_co2.v_sender_tracking TO 'tracking_reader';
-- GRANT SELECT ON swiftspan_co2.v_coordinator_workload TO 'tracking_reader';
-- REVOKE SELECT ON swiftspan_co2.v_coordinator_workload FROM 'tracking_reader';
-- GRANT 'tracking_reader' TO 'student_reader'@'localhost';
-- SET DEFAULT ROLE 'tracking_reader' TO 'student_reader'@'localhost';
-- A view is a stored query; it does not by itself enforce row-level identity or tenant isolation.
