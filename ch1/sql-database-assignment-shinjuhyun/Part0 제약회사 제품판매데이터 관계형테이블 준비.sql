/*
===============================================================================
SQL & 데이터베이스 통합 개인과제 공통 준비 SQL
기존 CSV Import 테이블을 관계형 테이블로 분리하는 완성본
===============================================================================

[전제]
- DBeaver에서 '제약회사_제품판매_데이터.csv'를 이미 아래 테이블로 Import한 상태입니다.
  public."제약회사_제품판매_데이터"

[실행 방법]
- 이 SQL 파일은 처음부터 끝까지 한 번에 실행하면 됩니다.
- 기존 public."제약회사_제품판매_데이터" 테이블을 원본으로 사용하므로 CSV 재Import 과정은 필요하지 않습니다.

[생성되는 관계형 테이블]
- product_groups
- products
- sales_departments
- customers
- sales
===============================================================================
*/


/* ============================================================================
0. 기존 관계형 테이블 삭제
============================================================================ */

DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS sales_departments;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS product_groups;


/* ============================================================================
1. 관계형 테이블 생성
============================================================================ */

CREATE TABLE product_groups (
    product_group_id   VARCHAR(10) PRIMARY KEY,
    product_group_name VARCHAR(100) NOT NULL
);

CREATE TABLE products (
    product_id           VARCHAR(10) PRIMARY KEY,
    product_group_id     VARCHAR(10) NOT NULL,
    product_name         VARCHAR(150) NOT NULL,
    dosage_form          VARCHAR(50),
    indication           VARCHAR(150),
    standard_unit_price  INTEGER,

    CONSTRAINT fk_products_group
        FOREIGN KEY (product_group_id)
        REFERENCES product_groups(product_group_id)
);

CREATE TABLE sales_departments (
    sales_dept_id   VARCHAR(10) PRIMARY KEY,
    sales_dept_name VARCHAR(100) NOT NULL,
    sales_region    VARCHAR(50),
    manager_name    VARCHAR(50)
);

CREATE TABLE customers (
    customer_id     VARCHAR(10) PRIMARY KEY,
    customer_name   VARCHAR(150) NOT NULL,
    customer_type   VARCHAR(50),
    customer_region VARCHAR(50),
    credit_grade    VARCHAR(5)
);

CREATE TABLE sales (
    sale_id          VARCHAR(20) PRIMARY KEY,
    sale_date        DATE NOT NULL,
    product_id       VARCHAR(10) NOT NULL,
    sales_dept_id    VARCHAR(10) NOT NULL,
    customer_id      VARCHAR(10) NOT NULL,
    sales_type       VARCHAR(50) NOT NULL,
    sales_channel    VARCHAR(50),
    quantity         INTEGER,
    unit_price       INTEGER,
    discount_rate    NUMERIC(6, 4),
    sale_amount      INTEGER,
    payment_method   VARCHAR(50),
    payment_status   VARCHAR(50),

    CONSTRAINT fk_sales_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id),

    CONSTRAINT fk_sales_department
        FOREIGN KEY (sales_dept_id)
        REFERENCES sales_departments(sales_dept_id),

    CONSTRAINT fk_sales_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
);


/* ============================================================================
2. 기존 CSV Import 테이블에서 관계형 테이블로 데이터 분리
============================================================================ */

/* 2-1. 제품군 */
INSERT INTO product_groups (
    product_group_id,
    product_group_name
)
SELECT DISTINCT ON (BTRIM("ProductGroupID"::text))
    BTRIM("ProductGroupID"::text),
    BTRIM("ProductGroupName"::text)
FROM public."제약회사_제품판매_데이터"
WHERE NULLIF(BTRIM("ProductGroupID"::text), '') IS NOT NULL
ORDER BY
    BTRIM("ProductGroupID"::text),
    BTRIM("ProductGroupName"::text);


/* 2-2. 제품 */
INSERT INTO products (
    product_id,
    product_group_id,
    product_name,
    dosage_form,
    indication,
    standard_unit_price
)
SELECT DISTINCT ON (BTRIM("ProductID"::text))
    BTRIM("ProductID"::text),
    BTRIM("ProductGroupID"::text),
    BTRIM("ProductName"::text),
    NULLIF(BTRIM("DosageForm"::text), ''),
    NULLIF(BTRIM("Indication"::text), ''),
    NULLIF(BTRIM("StandardUnitPrice"::text), '')::INTEGER
FROM public."제약회사_제품판매_데이터"
WHERE NULLIF(BTRIM("ProductID"::text), '') IS NOT NULL
ORDER BY
    BTRIM("ProductID"::text),
    BTRIM("ProductName"::text);


/* 2-3. 영업 부서 */
INSERT INTO sales_departments (
    sales_dept_id,
    sales_dept_name,
    sales_region,
    manager_name
)
SELECT DISTINCT ON (BTRIM("SalesDeptID"::text))
    BTRIM("SalesDeptID"::text),
    BTRIM("SalesDeptName"::text),
    NULLIF(BTRIM("SalesRegion"::text), ''),
    NULLIF(BTRIM("ManagerName"::text), '')
FROM public."제약회사_제품판매_데이터"
WHERE NULLIF(BTRIM("SalesDeptID"::text), '') IS NOT NULL
ORDER BY
    BTRIM("SalesDeptID"::text),
    BTRIM("SalesDeptName"::text);


/* 2-4. 거래처 */
INSERT INTO customers (
    customer_id,
    customer_name,
    customer_type,
    customer_region,
    credit_grade
)
SELECT DISTINCT ON (BTRIM("CustomerID"::text))
    BTRIM("CustomerID"::text),
    BTRIM("CustomerName"::text),
    NULLIF(BTRIM("CustomerType"::text), ''),
    NULLIF(BTRIM("CustomerRegion"::text), ''),
    NULLIF(BTRIM("CreditGrade"::text), '')
FROM public."제약회사_제품판매_데이터"
WHERE NULLIF(BTRIM("CustomerID"::text), '') IS NOT NULL
ORDER BY
    BTRIM("CustomerID"::text),
    BTRIM("CustomerName"::text);


/* 2-5. 판매 */
INSERT INTO sales (
    sale_id,
    sale_date,
    product_id,
    sales_dept_id,
    customer_id,
    sales_type,
    sales_channel,
    quantity,
    unit_price,
    discount_rate,
    sale_amount,
    payment_method,
    payment_status
)
SELECT
    BTRIM("SaleID"::text),
    NULLIF(BTRIM("SaleDate"::text), '')::DATE,
    BTRIM("ProductID"::text),
    BTRIM("SalesDeptID"::text),
    BTRIM("CustomerID"::text),
    BTRIM("SalesType"::text),
    NULLIF(BTRIM("SalesChannel"::text), ''),
    NULLIF(BTRIM("Quantity"::text), '')::INTEGER,
    NULLIF(BTRIM("UnitPrice"::text), '')::INTEGER,
    NULLIF(BTRIM("DiscountRate"::text), '')::NUMERIC(6, 4),
    NULLIF(BTRIM("SaleAmount"::text), '')::INTEGER,
    NULLIF(BTRIM("PaymentMethod"::text), ''),
    NULLIF(BTRIM("PaymentStatus"::text), '')
FROM public."제약회사_제품판매_데이터"
WHERE NULLIF(BTRIM("SaleID"::text), '') IS NOT NULL;


/* ============================================================================
3. 준비 결과 확인
============================================================================ */

SELECT '제약회사_제품판매_데이터' AS table_name, COUNT(*) AS row_count
FROM public."제약회사_제품판매_데이터"

UNION ALL

SELECT 'product_groups', COUNT(*)
FROM product_groups

UNION ALL

SELECT 'products', COUNT(*)
FROM products

UNION ALL

SELECT 'sales_departments', COUNT(*)
FROM sales_departments

UNION ALL

SELECT 'customers', COUNT(*)
FROM customers

UNION ALL

SELECT 'sales', COUNT(*)
FROM sales

ORDER BY table_name;


/*
===============================================================================
정상 결과 기준 - 제공 CSV 500행 기준
===============================================================================
원본_제약회사_제품판매_데이터 : 500
product_groups                : 6
products                      : 30
sales_departments             : 7
customers                     : 50
sales                         : 500
===============================================================================
*/

SELECT '제약회사_제품판매_데이터' AS table_name, COUNT(*) AS row_count FROM "제약회사_제품판매_데이터"
UNION ALL
SELECT 'product_groups', COUNT(*) FROM product_groups
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'sales_departments', COUNT(*) FROM sales_departments
UNION ALL
SELECT 'customers', COUNT(*) FROM customers
UNION ALL
SELECT 'sales', COUNT(*) FROM sales;