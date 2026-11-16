USE swiftspan_co2;

-- Shared metric definition: AdjustedIndex = Completion * VolumeWeight * RouteFactor.
-- Q1. Actor 1 observations in DispatchWave 4 with the weighted adjusted index.
SELECT s.SenderID, s.SenderName, sv.ServiceID, sv.ServiceCode, sv.ServiceName,
       o.DispatchWave, o.Completion, cp.ServiceBand, bp.RouteFactor,
       ROUND(o.Completion * sv.VolumeWeight * bp.RouteFactor, 4) AS AdjustedIndex
FROM bcnf_observation o
JOIN bcnf_sender s ON s.SenderID=o.SenderID
JOIN bcnf_service sv ON sv.ServiceID=o.ServiceID
JOIN bcnf_completion_policy cp ON cp.Completion=o.Completion
JOIN bcnf_service_band_policy bp ON bp.ServiceBand=cp.ServiceBand
WHERE o.SenderID=1 AND o.DispatchWave=4
ORDER BY sv.ServiceID;

-- Q2. Senders for which all five required services have all four wave observations >=39.
-- NOT EXISTS form avoids treating a missing observation as success.
SELECT s.SenderID, s.SenderName, s.RouteGroup
FROM bcnf_sender s
WHERE NOT EXISTS (
  SELECT 1
  FROM bcnf_group_required_service g
  CROSS JOIN dispatch_wave w
  WHERE g.RouteGroup=s.RouteGroup
    AND NOT EXISTS (
      SELECT 1 FROM bcnf_observation o
      WHERE o.SenderID=s.SenderID
        AND o.ServiceID=g.ServiceID
        AND o.DispatchWave=w.WaveValue
        AND o.Completion>=39
    )
)
ORDER BY s.SenderID;

-- Q3. Catalog services actually observed in wave 4 and with no sub-threshold value.
-- EXISTS prevents vacuous inclusion of a service with no wave-4 observation.
SELECT sv.ServiceID, sv.ServiceCode, sv.ServiceName
FROM bcnf_service sv
WHERE EXISTS (SELECT 1 FROM bcnf_observation o WHERE o.ServiceID=sv.ServiceID AND o.DispatchWave=4)
  AND NOT EXISTS (SELECT 1 FROM bcnf_observation o WHERE o.ServiceID=sv.ServiceID AND o.DispatchWave=4 AND o.Completion<39)
ORDER BY sv.ServiceID;

-- Q4. Coordinators whose observation-weighted mean is below their hub's weighted mean.
WITH coordinator_means AS (
  SELECT c.CoordinatorID, c.CoordinatorName, c.Hub, AVG(o.Completion) AS CoordMean, COUNT(*) AS N
  FROM bcnf_observation o
  JOIN bcnf_assignment a ON a.SenderID=o.SenderID AND a.ServiceID=o.ServiceID
  JOIN bcnf_coordinator c ON c.CoordinatorID=a.CoordinatorID
  GROUP BY c.CoordinatorID, c.CoordinatorName, c.Hub
), hub_means AS (
  SELECT c.Hub, AVG(o.Completion) AS HubMean
  FROM bcnf_observation o
  JOIN bcnf_assignment a ON a.SenderID=o.SenderID AND a.ServiceID=o.ServiceID
  JOIN bcnf_coordinator c ON c.CoordinatorID=a.CoordinatorID
  GROUP BY c.Hub
)
SELECT cm.CoordinatorID, cm.CoordinatorName, cm.Hub, cm.CoordMean, hm.HubMean, cm.N
FROM coordinator_means cm JOIN hub_means hm USING(Hub)
WHERE cm.CoordMean < hm.HubMean
ORDER BY cm.Hub, cm.CoordMean;

-- Q5. Senders with sub-threshold observations in at least three distinct waves.
SELECT s.SenderID, s.SenderName, COUNT(DISTINCT o.DispatchWave) AS LowWaves
FROM bcnf_sender s JOIN bcnf_observation o USING(SenderID)
WHERE o.Completion<39
GROUP BY s.SenderID, s.SenderName
HAVING COUNT(DISTINCT o.DispatchWave)>=3
ORDER BY s.SenderID;
