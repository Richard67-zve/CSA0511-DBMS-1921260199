USE meridian_museum;
-- Q1. Overdue loans that remain open.
SELECT loan_id, loan_no, lender_party_id, expected_return_date
FROM loan
WHERE actual_return_date IS NULL
  AND loan_status = 'ACTIVE'
  AND expected_return_date < CURRENT_DATE()
ORDER BY expected_return_date;

-- Q2. Artifacts with no condition report for any loan occurrence.
SELECT a.artifact_id, a.accession_no, a.title
FROM artifact a
LEFT JOIN loan_object lo ON lo.artifact_id = a.artifact_id
LEFT JOIN condition_report cr
  ON cr.loan_id = lo.loan_id AND cr.artifact_id = lo.artifact_id
WHERE cr.report_id IS NULL
ORDER BY a.artifact_id;

-- Q3. Full custody history for one artifact.
SELECT a.accession_no, l.loan_no, l.loan_status,
       lo.custody_start, lo.custody_end
FROM artifact a
JOIN loan_object lo ON lo.artifact_id = a.artifact_id
JOIN loan l ON l.loan_id = lo.loan_id
WHERE a.accession_no = 'MM-000003'
ORDER BY lo.custody_start;

-- Q4. Condition reports that require attention.
SELECT cr.report_id, a.accession_no, cr.report_date,
       cr.condition_code, cr.notes
FROM condition_report cr
JOIN artifact a ON a.artifact_id = cr.artifact_id
WHERE cr.condition_code IN ('POOR','DAMAGED')
ORDER BY cr.report_date DESC;

-- Q5. Loan and object counts by collection unit.
SELECT cu.unit_name, COUNT(DISTINCT lo.loan_id) AS loan_count,
       COUNT(DISTINCT lo.artifact_id) AS artifact_count
FROM collection_unit cu
JOIN artifact a ON a.unit_id = cu.unit_id
JOIN loan_object lo ON lo.artifact_id = a.artifact_id
GROUP BY cu.unit_id, cu.unit_name
ORDER BY cu.unit_name;

-- Q6. Exhibition slot occupancy and selected placed artifacts.
SELECT e.exhibition_code, e.exhibition_name, ds.slot_no,
       p.artifact_id, p.placement_start, p.placement_end
FROM exhibition e
JOIN display_slot ds ON ds.exhibition_id = e.exhibition_id
LEFT JOIN placement p
  ON p.exhibition_id = ds.exhibition_id AND p.slot_no = ds.slot_no
ORDER BY e.exhibition_id, ds.slot_no;

-- Q7. Current lender-facing notification contacts for open loans.
SELECT l.loan_no, nc.contact_label, nc.email, nc.phone,
       l.expected_return_date
FROM loan l
JOIN loan_notification_contact lnc ON lnc.loan_id = l.loan_id
JOIN notification_contact nc ON nc.contact_id = lnc.contact_id
WHERE l.actual_return_date IS NULL;

-- Q8. Latest condition evidence per artifact.
SELECT a.accession_no, cr.report_date, cr.report_stage,
       cr.condition_code, cr.inspector_person_id
FROM artifact a
JOIN condition_report cr ON cr.artifact_id = a.artifact_id
WHERE cr.report_date = (
    SELECT MAX(cr2.report_date)
    FROM condition_report cr2
    WHERE cr2.artifact_id = a.artifact_id
)
ORDER BY a.accession_no;

-- Task 12 migration-integrity checks after co-ownership redesign.
-- Q9. Ownership share totals not equal to 100 on a selected date.
SELECT a.artifact_id, COALESCE(SUM(ao.share_percent),0) AS total_share
FROM artifact a
LEFT JOIN artifact_owner ao
  ON ao.artifact_id = a.artifact_id
 AND ao.valid_from <= '2026-12-01'
 AND (ao.valid_to IS NULL OR ao.valid_to >= '2026-12-01')
GROUP BY a.artifact_id
HAVING ABS(COALESCE(SUM(ao.share_percent),0) - 100.00) > 0.01;

-- Q10. Overlapping validity intervals for the same artifact/owner.
SELECT a.artifact_id, a.party_id, a.valid_from, b.valid_from
FROM artifact_owner a
JOIN artifact_owner b
  ON a.artifact_id = b.artifact_id
 AND a.party_id = b.party_id
 AND a.valid_from < b.valid_from
 AND a.valid_from <= COALESCE(b.valid_to, '9999-12-31')
 AND COALESCE(a.valid_to, '9999-12-31') >= b.valid_from;
