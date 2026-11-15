-- Meridian Museum - Assignment 1 CO1
-- Target: MySQL 8.0.16+ (CHECK constraints are enforced from 8.0.16)
-- Baseline model before Task 12: each artifact has one current legal owner.
CREATE DATABASE IF NOT EXISTS meridian_museum
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE meridian_museum;

SET FOREIGN_KEY_CHECKS = 0;
DROP VIEW IF EXISTS v_current_custody;
DROP VIEW IF EXISTS v_artifact_current_owner;
DROP TABLE IF EXISTS condition_report;
DROP TABLE IF EXISTS placement;
DROP TABLE IF EXISTS display_slot;
DROP TABLE IF EXISTS exhibition;
DROP TABLE IF EXISTS loan_object;
DROP TABLE IF EXISTS loan_notification_contact;
DROP TABLE IF EXISTS notification_contact;
DROP TABLE IF EXISTS loan;
DROP TABLE IF EXISTS artifact;
DROP TABLE IF EXISTS collection_type;
DROP TABLE IF EXISTS collection_unit;
DROP TABLE IF EXISTS registrar;
DROP TABLE IF EXISTS curator;
DROP TABLE IF EXISTS employee;
DROP TABLE IF EXISTS lender;
DROP TABLE IF EXISTS person_phone;
DROP TABLE IF EXISTS organization;
DROP TABLE IF EXISTS person;
DROP TABLE IF EXISTS party;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE party (
    party_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    party_kind ENUM('PERSON','ORGANIZATION') NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE person (
    party_id BIGINT PRIMARY KEY,
    first_name VARCHAR(80) NOT NULL,
    middle_name VARCHAR(80) NULL,
    last_name VARCHAR(80) NOT NULL,
    email VARCHAR(254) NULL,
    FOREIGN KEY (party_id) REFERENCES party(party_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE organization (
    party_id BIGINT PRIMARY KEY,
    legal_name VARCHAR(180) NOT NULL,
    registration_no VARCHAR(80) NULL UNIQUE,
    FOREIGN KEY (party_id) REFERENCES party(party_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE person_phone (
    party_id BIGINT NOT NULL,
    phone_type VARCHAR(25) NOT NULL,
    phone_number VARCHAR(30) NOT NULL,
    PRIMARY KEY (party_id, phone_type, phone_number),
    FOREIGN KEY (party_id) REFERENCES person(party_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE lender (
    party_id BIGINT PRIMARY KEY,
    lender_code VARCHAR(30) NOT NULL UNIQUE,
    joined_on DATE NOT NULL,
    FOREIGN KEY (party_id) REFERENCES party(party_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE employee (
    person_id BIGINT PRIMARY KEY,
    employee_no VARCHAR(30) NOT NULL UNIQUE,
    role ENUM('CURATOR','REGISTRAR') NOT NULL,
    hired_on DATE NOT NULL,
    FOREIGN KEY (person_id) REFERENCES person(party_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE curator (
    person_id BIGINT PRIMARY KEY,
    specialisation VARCHAR(100) NOT NULL,
    FOREIGN KEY (person_id) REFERENCES employee(person_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE registrar (
    person_id BIGINT PRIMARY KEY,
    clearance_level VARCHAR(30) NOT NULL,
    FOREIGN KEY (person_id) REFERENCES employee(person_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE collection_unit (
    unit_id SMALLINT PRIMARY KEY,
    unit_name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE collection_type (
    collection_type_id SMALLINT PRIMARY KEY,
    type_name VARCHAR(80) NOT NULL UNIQUE,
    description VARCHAR(255) NULL
) ENGINE=InnoDB;

CREATE TABLE artifact (
    artifact_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    accession_no VARCHAR(40) NOT NULL UNIQUE,
    unit_id SMALLINT NOT NULL,
    collection_type_id SMALLINT NOT NULL,
    owner_party_id BIGINT NOT NULL,
    title VARCHAR(200) NOT NULL,
    estimated_value DECIMAL(14,2) NULL,
    currency_code CHAR(3) NOT NULL DEFAULT 'INR',
    ownership_known_from DATE NULL,
    acquired_on DATE NULL,
    FOREIGN KEY (unit_id) REFERENCES collection_unit(unit_id) ON DELETE RESTRICT,
    FOREIGN KEY (collection_type_id) REFERENCES collection_type(collection_type_id) ON DELETE RESTRICT,
    CONSTRAINT fk_artifact_owner_party FOREIGN KEY (owner_party_id) REFERENCES party(party_id) ON DELETE RESTRICT,
    CHECK (estimated_value IS NULL OR estimated_value >= 0)
) ENGINE=InnoDB;

CREATE TABLE loan (
    loan_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    loan_no VARCHAR(40) NOT NULL UNIQUE,
    lender_party_id BIGINT NOT NULL,
    responsible_curator_id BIGINT NOT NULL,
    processing_registrar_id BIGINT NOT NULL,
    loan_date DATE NOT NULL,
    expected_return_date DATE NOT NULL,
    actual_return_date DATE NULL,
    loan_status ENUM('DRAFT','APPROVED','ACTIVE','CLOSED','CANCELLED') NOT NULL,
    purpose VARCHAR(255) NOT NULL,
    FOREIGN KEY (lender_party_id) REFERENCES lender(party_id) ON DELETE RESTRICT,
    FOREIGN KEY (responsible_curator_id) REFERENCES curator(person_id) ON DELETE RESTRICT,
    FOREIGN KEY (processing_registrar_id) REFERENCES registrar(person_id) ON DELETE RESTRICT,
    CHECK (expected_return_date >= loan_date),
    CHECK (actual_return_date IS NULL OR actual_return_date >= loan_date)
) ENGINE=InnoDB;

CREATE TABLE loan_object (
    loan_id BIGINT NOT NULL,
    artifact_id BIGINT NOT NULL,
    custody_start DATE NOT NULL,
    custody_end DATE NULL,
    loan_line_description VARCHAR(200) NOT NULL,
    loan_line_value DECIMAL(14,2) NOT NULL,
    currency_code CHAR(3) NOT NULL DEFAULT 'INR',
    PRIMARY KEY (loan_id, artifact_id),
    FOREIGN KEY (loan_id) REFERENCES loan(loan_id) ON DELETE RESTRICT,
    FOREIGN KEY (artifact_id) REFERENCES artifact(artifact_id) ON DELETE RESTRICT,
    CHECK (custody_end IS NULL OR custody_end >= custody_start),
    CHECK (loan_line_value >= 0),
    INDEX ix_loan_object_artifact_dates (artifact_id, custody_start, custody_end)
) ENGINE=InnoDB;

CREATE TABLE exhibition (
    exhibition_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    exhibition_code VARCHAR(30) NOT NULL UNIQUE,
    exhibition_name VARCHAR(160) NOT NULL,
    opens_on DATE NOT NULL,
    closes_on DATE NOT NULL,
    CHECK (closes_on >= opens_on)
) ENGINE=InnoDB;

-- Weak entity: a slot number is unique only within its owning exhibition.
CREATE TABLE display_slot (
    exhibition_id BIGINT NOT NULL,
    slot_no SMALLINT NOT NULL,
    gallery_name VARCHAR(80) NOT NULL,
    position_description VARCHAR(160) NOT NULL,
    PRIMARY KEY (exhibition_id, slot_no),
    FOREIGN KEY (exhibition_id) REFERENCES exhibition(exhibition_id) ON DELETE RESTRICT,
    CHECK (slot_no > 0)
) ENGINE=InnoDB;

CREATE TABLE placement (
    placement_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    loan_id BIGINT NOT NULL,
    artifact_id BIGINT NOT NULL,
    exhibition_id BIGINT NOT NULL,
    slot_no SMALLINT NOT NULL,
    placement_start DATE NOT NULL,
    placement_end DATE NULL,
    display_caption VARCHAR(200) NULL,
    FOREIGN KEY (loan_id, artifact_id) REFERENCES loan_object(loan_id, artifact_id) ON DELETE RESTRICT,
    FOREIGN KEY (exhibition_id, slot_no) REFERENCES display_slot(exhibition_id, slot_no) ON DELETE RESTRICT,
    CHECK (placement_end IS NULL OR placement_end >= placement_start),
    INDEX ix_placement_slot_dates (exhibition_id, slot_no, placement_start, placement_end)
) ENGINE=InnoDB;

CREATE TABLE notification_contact (
    contact_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    person_id BIGINT NULL,
    organization_id BIGINT NULL,
    contact_label VARCHAR(100) NOT NULL,
    email VARCHAR(254) NULL,
    phone VARCHAR(30) NULL,
    FOREIGN KEY (person_id) REFERENCES person(party_id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id) REFERENCES organization(party_id) ON DELETE RESTRICT,
    CHECK ((person_id IS NOT NULL AND organization_id IS NULL) OR
           (person_id IS NULL AND organization_id IS NOT NULL))
) ENGINE=InnoDB;

CREATE TABLE loan_notification_contact (
    loan_id BIGINT NOT NULL,
    contact_id BIGINT NOT NULL,
    notification_purpose VARCHAR(40) NOT NULL,
    PRIMARY KEY (loan_id, contact_id, notification_purpose),
    FOREIGN KEY (loan_id) REFERENCES loan(loan_id) ON DELETE RESTRICT,
    FOREIGN KEY (contact_id) REFERENCES notification_contact(contact_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Each report is evidence owned by one LOAN_OBJECT occurrence, not by the lender.
CREATE TABLE condition_report (
    report_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    loan_id BIGINT NOT NULL,
    artifact_id BIGINT NOT NULL,
    inspector_person_id BIGINT NOT NULL,
    report_date DATE NOT NULL,
    report_stage ENUM('RECEIPT','DURING_CUSTODY','RETURN') NOT NULL,
    condition_code ENUM('EXCELLENT','GOOD','FAIR','POOR','DAMAGED') NOT NULL,
    notes TEXT NOT NULL,
    FOREIGN KEY (loan_id, artifact_id) REFERENCES loan_object(loan_id, artifact_id) ON DELETE RESTRICT,
    FOREIGN KEY (inspector_person_id) REFERENCES employee(person_id) ON DELETE RESTRICT,
    INDEX ix_condition_artifact_date (artifact_id, report_date)
) ENGINE=InnoDB;

-- Views preserve stable operational query interfaces.
CREATE VIEW v_current_custody AS
SELECT a.artifact_id, a.accession_no, a.title, l.loan_id, l.loan_no,
       l.lender_party_id, lo.custody_start, lo.custody_end
FROM artifact a
JOIN loan_object lo ON lo.artifact_id = a.artifact_id
JOIN loan l ON l.loan_id = lo.loan_id
WHERE lo.custody_end IS NULL;

CREATE VIEW v_artifact_current_owner AS
SELECT a.artifact_id, a.accession_no, a.title, a.owner_party_id
FROM artifact a;

-- Row-level trigger: prevent overlapping custody periods for a physical artifact.
DELIMITER $$
CREATE TRIGGER trg_loan_object_no_overlap_insert
BEFORE INSERT ON loan_object
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT 1 FROM loan_object x
        WHERE x.artifact_id = NEW.artifact_id
          AND NEW.custody_start <= COALESCE(x.custody_end, '9999-12-31')
          AND COALESCE(NEW.custody_end, '9999-12-31') >= x.custody_start
    ) THEN
        SIGNAL SQLSTATE '45000'
          SET MESSAGE_TEXT = 'Overlapping custody period for artifact';
    END IF;
END$$

CREATE TRIGGER trg_person_party_kind_insert
BEFORE INSERT ON person
FOR EACH ROW
BEGIN
    IF (SELECT party_kind FROM party WHERE party_id = NEW.party_id) <> 'PERSON' THEN
        SIGNAL SQLSTATE '45000'
          SET MESSAGE_TEXT = 'PERSON subtype requires PARTY kind PERSON';
    END IF;
END$$

CREATE TRIGGER trg_organization_party_kind_insert
BEFORE INSERT ON organization
FOR EACH ROW
BEGIN
    IF (SELECT party_kind FROM party WHERE party_id = NEW.party_id) <> 'ORGANIZATION' THEN
        SIGNAL SQLSTATE '45000'
          SET MESSAGE_TEXT = 'ORGANIZATION subtype requires PARTY kind ORGANIZATION';
    END IF;
END$$

CREATE TRIGGER trg_curator_role_insert
BEFORE INSERT ON curator
FOR EACH ROW
BEGIN
    IF (SELECT role FROM employee WHERE person_id = NEW.person_id) <> 'CURATOR' THEN
        SIGNAL SQLSTATE '45000'
          SET MESSAGE_TEXT = 'CURATOR subtype requires employee role CURATOR';
    END IF;
END$$

CREATE TRIGGER trg_curator_role_update
BEFORE UPDATE ON curator
FOR EACH ROW
BEGIN
    IF (SELECT role FROM employee WHERE person_id = NEW.person_id) <> 'CURATOR' THEN
        SIGNAL SQLSTATE '45000'
          SET MESSAGE_TEXT = 'CURATOR subtype requires employee role CURATOR';
    END IF;
END$$

CREATE TRIGGER trg_registrar_role_insert
BEFORE INSERT ON registrar
FOR EACH ROW
BEGIN
    IF (SELECT role FROM employee WHERE person_id = NEW.person_id) <> 'REGISTRAR' THEN
        SIGNAL SQLSTATE '45000'
          SET MESSAGE_TEXT = 'REGISTRAR subtype requires employee role REGISTRAR';
    END IF;
END$$

CREATE TRIGGER trg_registrar_role_update
BEFORE UPDATE ON registrar
FOR EACH ROW
BEGIN
    IF (SELECT role FROM employee WHERE person_id = NEW.person_id) <> 'REGISTRAR' THEN
        SIGNAL SQLSTATE '45000'
          SET MESSAGE_TEXT = 'REGISTRAR subtype requires employee role REGISTRAR';
    END IF;
END$$

CREATE TRIGGER trg_placement_no_slot_overlap
BEFORE INSERT ON placement
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT 1 FROM placement p
        WHERE p.exhibition_id = NEW.exhibition_id
          AND p.slot_no = NEW.slot_no
          AND NEW.placement_start <= COALESCE(p.placement_end, '9999-12-31')
          AND COALESCE(NEW.placement_end, '9999-12-31') >= p.placement_start
    ) THEN
        SIGNAL SQLSTATE '45000'
          SET MESSAGE_TEXT = 'Overlapping placement in display slot';
    END IF;
END$$
CREATE TRIGGER trg_loan_object_no_overlap_update
BEFORE UPDATE ON loan_object
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT 1 FROM loan_object x
        WHERE x.artifact_id = NEW.artifact_id
          AND NOT (x.loan_id = OLD.loan_id AND x.artifact_id = OLD.artifact_id)
          AND NEW.custody_start <= COALESCE(x.custody_end, '9999-12-31')
          AND COALESCE(NEW.custody_end, '9999-12-31') >= x.custody_start
    ) THEN
        SIGNAL SQLSTATE '45000'
          SET MESSAGE_TEXT = 'Overlapping custody period for artifact';
    END IF;
END$$

CREATE TRIGGER trg_placement_no_slot_overlap_update
BEFORE UPDATE ON placement
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT 1 FROM placement p
        WHERE p.exhibition_id = NEW.exhibition_id
          AND p.slot_no = NEW.slot_no
          AND p.placement_id <> OLD.placement_id
          AND NEW.placement_start <= COALESCE(p.placement_end, '9999-12-31')
          AND COALESCE(NEW.placement_end, '9999-12-31') >= p.placement_start
    ) THEN
        SIGNAL SQLSTATE '45000'
          SET MESSAGE_TEXT = 'Overlapping placement in display slot';
    END IF;
END$$
DELIMITER ;

-- Important cross-row rules that remain transaction/service-level:
-- 1. A display slot cannot have overlapping active placements.
-- 2. A curator must be the curator employee subtype (FK enforces this).
-- 3. During Task 12, owner shares per artifact/date must total exactly 100.
-- 4. Referential checks do not by themselves prove that placement dates fall
--    inside both the loan-object custody period and the exhibition open period.
