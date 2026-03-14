-- ============================================================
-- warehouse/schema.sql
-- Insurance Policy Data Warehouse — MySQL DDL
-- ============================================================
-- Run once to create the database and all tables.
-- Then use warehouse/load_mysql.py to load data from CSVs.
-- ============================================================

CREATE DATABASE IF NOT EXISTS insurance_dw
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE insurance_dw;

-- ────────────────────────────────────────────────────────────
-- DIMENSION: dim_customer  (SCD Type 2)
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_customer (
    Customer_SK          INT            NOT NULL AUTO_INCREMENT,
    Customer_ID          INT            NOT NULL,
    Customer_Title       VARCHAR(30),
    Customer_First_Name  VARCHAR(100)   NOT NULL,
    Customer_Last_Name   VARCHAR(100)   NOT NULL,
    Customer_Name        VARCHAR(220),
    Customer_Segment     VARCHAR(50),
    Marital_Status       VARCHAR(20),
    Gender               VARCHAR(10),
    DOB                  DATE,
    Effective_Start_Dt   DATE,
    Effective_End_Dt     DATE,
    Region               VARCHAR(10),
    PRIMARY KEY (Customer_SK),
    INDEX idx_cust_id  (Customer_ID),
    INDEX idx_region   (Region),
    INDEX idx_marital  (Marital_Status)
) ENGINE=InnoDB;


-- ────────────────────────────────────────────────────────────
-- DIMENSION: dim_policy  (SCD Type 2 on Policy_Type_Id)
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_policy (
    Policy_SK            INT            NOT NULL AUTO_INCREMENT,
    Policy_Type_Id       VARCHAR(10),
    Policy_Type          VARCHAR(50),
    Policy_Type_Desc     VARCHAR(200),
    Policy_Id            BIGINT         NOT NULL,
    Policy_Name          VARCHAR(200),
    Customer_ID          INT,
    Premium_Amt          DECIMAL(15,2),
    Policy_Term          VARCHAR(20),
    Policy_Start_Dt      DATE,
    Policy_End_Dt        DATE,
    Next_Premium_Dt      DATE,
    Actual_Premium_Paid_Dt DATE,
    Total_Policy_Amt     DECIMAL(15,2),
    Premium_Amt_Paid_TillDate DECIMAL(15,2),
    Num_Installments     INT,
    Region               VARCHAR(10),
    PRIMARY KEY (Policy_SK),
    INDEX idx_pol_id     (Policy_Id),
    INDEX idx_pol_cust   (Customer_ID),
    INDEX idx_pol_type   (Policy_Type),
    INDEX idx_pol_term   (Policy_Term),
    INDEX idx_pol_region (Region),
    INDEX idx_pol_start  (Policy_Start_Dt)
) ENGINE=InnoDB;


-- ────────────────────────────────────────────────────────────
-- DIMENSION: dim_address
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_address (
    Address_SK    INT         NOT NULL AUTO_INCREMENT,
    Customer_ID   INT,
    Country       VARCHAR(60),
    Region        VARCHAR(10),
    State         VARCHAR(60),
    City          VARCHAR(60),
    Postal_Code   VARCHAR(20),
    PRIMARY KEY (Address_SK),
    INDEX idx_addr_cust   (Customer_ID),
    INDEX idx_addr_region (Region)
) ENGINE=InnoDB;


-- ────────────────────────────────────────────────────────────
-- FACT: fact_transactions
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_transactions (
    Transaction_SK            INT            NOT NULL AUTO_INCREMENT,
    Policy_Id                 BIGINT,
    Customer_ID               INT,
    Customer_SK               INT,
    Policy_SK                 INT,
    Address_SK                INT,
    Premium_Amt               DECIMAL(15,2),
    Total_Policy_Amt          DECIMAL(15,2),
    Premium_Amt_Paid_TillDate DECIMAL(15,2),
    Next_Premium_Dt           DATE,
    Actual_Premium_Paid_Dt    DATE,
    Is_Late                   TINYINT(1)    DEFAULT 0,
    Late_Fee                  DECIMAL(15,2) DEFAULT 0.00,
    Region                    VARCHAR(10),
    PRIMARY KEY (Transaction_SK),
    INDEX idx_tx_cust    (Customer_ID),
    INDEX idx_tx_policy  (Policy_Id),
    INDEX idx_tx_csk     (Customer_SK),
    INDEX idx_tx_psk     (Policy_SK),
    INDEX idx_tx_region  (Region),
    INDEX idx_tx_paid_dt (Actual_Premium_Paid_Dt),
    CONSTRAINT fk_tx_cust FOREIGN KEY (Customer_SK)
        REFERENCES dim_customer(Customer_SK) ON DELETE SET NULL,
    CONSTRAINT fk_tx_pol  FOREIGN KEY (Policy_SK)
        REFERENCES dim_policy(Policy_SK)   ON DELETE SET NULL,
    CONSTRAINT fk_tx_addr FOREIGN KEY (Address_SK)
        REFERENCES dim_address(Address_SK) ON DELETE SET NULL
) ENGINE=InnoDB;


-- ============================================================
-- ANALYTICS VIEWS — queries b through g
-- ============================================================

-- b) Customers who changed policy type
CREATE OR REPLACE VIEW vw_policy_changes AS
SELECT
    p_curr.Customer_ID,
    CONCAT(c.Customer_Title, ' ', c.Customer_First_Name, ' ', c.Customer_Last_Name) AS Customer_Name,
    p_curr.Policy_Id,
    p_curr.Policy_Type_Id   AS Current_Policy_Type_Id,
    p_curr.Policy_Type      AS Current_Policy_Type,
    p_curr.Policy_Name      AS Current_Policy_Name,
    p_prev.Policy_Type_Id   AS Previous_Policy_Type_Id,
    p_prev.Policy_Type      AS Previous_Policy_Type,
    p_prev.Policy_Name      AS Previous_Policy_Name
FROM dim_policy p_curr
JOIN dim_policy p_prev
    ON p_curr.Policy_Id = p_prev.Policy_Id
   AND p_curr.Policy_SK <> p_prev.Policy_SK
   AND p_curr.Policy_Type_Id <> p_prev.Policy_Type_Id
LEFT JOIN dim_customer c
    ON c.Customer_ID = p_curr.Customer_ID
   AND (c.Effective_End_Dt IS NULL OR c.Effective_End_Dt = '');


-- c) Total policy amount by all customers and all regions
CREATE OR REPLACE VIEW vw_total_policy_all AS
SELECT
    c.Customer_ID,
    CONCAT(c.Customer_Title,' ',c.Customer_First_Name,' ',c.Customer_Last_Name) AS Customer_Name,
    'All' AS Region,
    SUM(f.Total_Policy_Amt) AS Total_Policy_Amt
FROM fact_transactions f
JOIN dim_customer c
    ON f.Customer_SK = c.Customer_SK
GROUP BY c.Customer_ID, Customer_Name
ORDER BY Total_Policy_Amt DESC;


-- d) Total policy amount — Auto policy customers
CREATE OR REPLACE VIEW vw_auto_policy_amount AS
SELECT
    c.Customer_ID,
    CONCAT(c.Customer_Title,' ',c.Customer_First_Name,' ',c.Customer_Last_Name) AS Customer_Name,
    'All'  AS Region,
    'Auto' AS Policy_Type,
    SUM(f.Total_Policy_Amt) AS Total_Policy_Amt
FROM fact_transactions f
JOIN dim_customer c  ON f.Customer_SK = c.Customer_SK
JOIN dim_policy   p  ON f.Policy_SK  = p.Policy_SK
WHERE LOWER(p.Policy_Type) = 'auto'
GROUP BY c.Customer_ID, Customer_Name
ORDER BY Total_Policy_Amt DESC;


-- e) East+West, Quarterly, 2012
CREATE OR REPLACE VIEW vw_east_west_quarterly_2012 AS
SELECT
    c.Customer_ID,
    CONCAT(c.Customer_Title,' ',c.Customer_First_Name,' ',c.Customer_Last_Name) AS Customer_Name,
    'East and West'   AS Region,
    p.Policy_Term,
    p.Policy_Start_Dt,
    SUM(f.Total_Policy_Amt) AS Total_Policy_Amt
FROM fact_transactions f
JOIN dim_customer c ON f.Customer_SK = c.Customer_SK
JOIN dim_policy   p ON f.Policy_SK  = p.Policy_SK
WHERE p.Region IN ('EAST','WEST')
  AND p.Policy_Term = 'Quarterly'
  AND YEAR(p.Policy_Start_Dt) = 2012
GROUP BY c.Customer_ID, Customer_Name, p.Policy_Term, p.Policy_Start_Dt
ORDER BY Total_Policy_Amt DESC;


-- f) Marital status changes (SCD)
CREATE OR REPLACE VIEW vw_marital_changes AS
SELECT
    c1.Customer_ID,
    c1.Customer_Title,
    c1.Customer_First_Name,
    c1.Customer_Last_Name,
    c1.Customer_Segment,
    c1.Marital_Status,
    c1.Effective_Start_Dt AS Start_Dt_Marital_Status,
    c1.Effective_End_Dt   AS End_Dt_Marital_Status
FROM dim_customer c1
WHERE c1.Customer_ID IN (
    SELECT Customer_ID
    FROM dim_customer
    GROUP BY Customer_ID
    HAVING COUNT(DISTINCT Marital_Status) > 1
)
ORDER BY c1.Customer_ID, c1.Effective_Start_Dt;


-- g) All regions — full customer + policy + address view
CREATE OR REPLACE VIEW vw_all_regions_full AS
SELECT
    c.Customer_ID,
    c.Customer_Name,
    c.Customer_Segment,
    c.Marital_Status,
    c.Gender,
    c.Region,
    p.Policy_Id,
    p.Policy_Type_Id,
    p.Policy_Type,
    p.Policy_Type_Desc,
    p.Policy_Name,
    p.Policy_Term,
    p.Policy_Start_Dt,
    p.Policy_End_Dt,
    p.Premium_Amt,
    p.Total_Policy_Amt,
    a.Country,
    a.State,
    a.City,
    a.Postal_Code,
    f.Is_Late,
    f.Late_Fee
FROM dim_customer c
LEFT JOIN fact_transactions f  ON c.Customer_SK  = f.Customer_SK
LEFT JOIN dim_policy        p  ON f.Policy_SK    = p.Policy_SK
LEFT JOIN dim_address       a  ON f.Address_SK   = a.Address_SK
ORDER BY c.Region, c.Customer_ID;
