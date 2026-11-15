-- Task 12: replace one-owner-per-artifact with effective-dated co-ownership.
-- Run after 01_schema_mysql.sql, after taking a backup and checking source dates.
USE meridian_museum;

CREATE TABLE artifact_owner (
    artifact_id BIGINT NOT NULL,
    party_id BIGINT NOT NULL,
    share_percent DECIMAL(5,2) NOT NULL,
    valid_from DATE NOT NULL,
    valid_to DATE NULL,
    source_quality ENUM('VERIFIED_HISTORY','MIGRATION_BASELINE_UNKNOWN_START','MIGRATED_KNOWN_START')
        NOT NULL DEFAULT 'VERIFIED_HISTORY',
    PRIMARY KEY (artifact_id, party_id, valid_from),
    FOREIGN KEY (artifact_id) REFERENCES artifact(artifact_id) ON DELETE RESTRICT,
    FOREIGN KEY (party_id) REFERENCES party(party_id) ON DELETE RESTRICT,
    CHECK (share_percent > 0 AND share_percent <= 100),
    CHECK (valid_to IS NULL OR valid_to >= valid_from),
    INDEX ix_artifact_owner_timeline (artifact_id, valid_from, valid_to),
    INDEX ix_party_ownership (party_id, artifact_id)
) ENGINE=InnoDB;

-- Backfill the baseline single owner. If a verified historical effective date
-- is absent, use the migration date and explicitly flag the unknown start.
INSERT INTO artifact_owner
    (artifact_id, party_id, share_percent, valid_from, valid_to, source_quality)
SELECT artifact_id, owner_party_id, 100.00,
       COALESCE(ownership_known_from, CURRENT_DATE()), NULL,
       CASE WHEN ownership_known_from IS NULL
            THEN 'MIGRATION_BASELINE_UNKNOWN_START'
            ELSE 'MIGRATED_KNOWN_START' END
FROM artifact;

-- The canonical ownership interface keeps an artifact-level row but lists
-- multiple owners. Consumers should use this view, not infer ownership from loan.
-- The current-custody view from Task 7 is unchanged: loan custody does not
-- depend on who owns the artifact. This ownership summary is a separate view.
CREATE OR REPLACE VIEW v_artifact_current_owner AS
SELECT a.artifact_id, a.accession_no, a.title,
       GROUP_CONCAT(CONCAT(ao.party_id, ':', ao.share_percent, '%')
                    ORDER BY ao.party_id SEPARATOR '; ') AS current_owner_summary,
       SUM(ao.share_percent) AS total_share_percent
FROM artifact a
JOIN artifact_owner ao ON ao.artifact_id = a.artifact_id
WHERE ao.valid_from <= CURRENT_DATE()
  AND (ao.valid_to IS NULL OR ao.valid_to >= CURRENT_DATE())
GROUP BY a.artifact_id, a.accession_no, a.title;

-- After verifying the view and backfill, remove the old single-owner column.
ALTER TABLE artifact DROP FOREIGN KEY fk_artifact_owner_party;
ALTER TABLE artifact DROP COLUMN owner_party_id;

-- Ownership transition protocol (all rows for the transition are one transaction):
-- 1) Close old intervals at the day before the new effective date.
-- 2) Insert the new owner-share rows, whose percentages sum to 100.
-- 3) Run the validation query below before COMMIT.
-- 4) Never delete historical ownership rows.
--
-- Example validation for a chosen date (replace values):
-- SELECT artifact_id, SUM(share_percent) AS total_share
-- FROM artifact_owner
-- WHERE artifact_id = 1001 AND valid_from <= '2026-12-01'
--   AND (valid_to IS NULL OR valid_to >= '2026-12-01')
-- GROUP BY artifact_id
-- HAVING ABS(SUM(share_percent) - 100.00) > 0.01;
-- The expected result is empty. A stored procedure/service transaction should
-- reject a transition if any artifact/date interval does not total 100.


DELIMITER $$
CREATE TRIGGER trg_artifact_owner_no_overlap
BEFORE INSERT ON artifact_owner
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT 1 FROM artifact_owner x
        WHERE x.artifact_id = NEW.artifact_id
          AND x.party_id = NEW.party_id
          AND NEW.valid_from <= COALESCE(x.valid_to, '9999-12-31')
          AND COALESCE(NEW.valid_to, '9999-12-31') >= x.valid_from
    ) THEN
        SIGNAL SQLSTATE '45000'
          SET MESSAGE_TEXT = 'Overlapping ownership interval for artifact and party';
    END IF;
END$$

CREATE TRIGGER trg_artifact_owner_no_overlap_update
BEFORE UPDATE ON artifact_owner
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT 1 FROM artifact_owner x
        WHERE x.artifact_id = NEW.artifact_id
          AND x.party_id = NEW.party_id
          AND NOT (x.artifact_id = OLD.artifact_id
                   AND x.party_id = OLD.party_id
                   AND x.valid_from = OLD.valid_from)
          AND NEW.valid_from <= COALESCE(x.valid_to, '9999-12-31')
          AND COALESCE(NEW.valid_to, '9999-12-31') >= x.valid_from
    ) THEN
        SIGNAL SQLSTATE '45000'
          SET MESSAGE_TEXT = 'Overlapping ownership interval for artifact and party';
    END IF;
END$$

CREATE PROCEDURE sp_validate_artifact_owner_shares(
    IN p_artifact_id BIGINT,
    IN p_as_of DATE
)
BEGIN
    DECLARE v_total DECIMAL(7,2) DEFAULT 0.00;
    SELECT COALESCE(SUM(share_percent),0.00) INTO v_total
    FROM artifact_owner
    WHERE artifact_id = p_artifact_id
      AND valid_from <= p_as_of
      AND (valid_to IS NULL OR valid_to >= p_as_of);
    IF ABS(v_total - 100.00) > 0.01 THEN
        SIGNAL SQLSTATE '45000'
          SET MESSAGE_TEXT = 'Ownership shares for artifact/date must total 100 percent';
    END IF;
END$$
DELIMITER ;

-- Call the validation procedure for every artifact/date in the transition
-- transaction before COMMIT. The procedure is intentionally explicit because
-- MySQL CHECK constraints cannot aggregate multiple rows.
