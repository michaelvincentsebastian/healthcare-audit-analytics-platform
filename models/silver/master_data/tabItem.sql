MODEL (
  name silver.tabItem,
  kind FULL,
  grain (name)
);

-- Preprocessing only: cleaned CURRENT-STATE snapshot of bronze.tabItem.
-- Table name kept identical to bronze/upstream MariaDB source (tabItem)
-- so lineage stays 1:1 -- no renaming, no reshaping.
--
-- Why the QUALIFY dedup exists: bronze is INCREMENTAL_BY_TIME_RANGE keyed on
-- `modified`, so an item edited more than once (e.g. price change) can
-- legitimately produce >1 row per `name` across load windows. Without dedup,
-- `grain (name)` above is a label SQLMesh won't actually be able to verify.
-- This QUALIFY keeps only the latest row per `name`.
-- Changes vs. raw bronze:
--   * Keep only the most-recently-modified row per `name` (current state).
--   * VARCHAR columns: TRIM()'d, blank string ('') -> NULL.
--   * No casing changes, no business logic
--     (joins happen in models/silver/join, business rules in gold).

SELECT
    NULLIF(TRIM(name), '') AS name,
    creation,
    modified,
    NULLIF(TRIM(modified_by), '') AS modified_by,
    NULLIF(TRIM(owner), '') AS owner,
    docstatus,
    idx,
    NULLIF(TRIM(naming_series), '') AS naming_series,
    NULLIF(TRIM(item_code), '') AS item_code,
    NULLIF(TRIM(item_name), '') AS item_name,
    NULLIF(TRIM(item_group), '') AS item_group,
    NULLIF(TRIM(stock_uom), '') AS stock_uom,
    disabled,
    allow_alternative_item,
    is_stock_item,
    has_variants,
    opening_stock,
    valuation_rate,
    standard_rate,
    is_fixed_asset,
    auto_create_assets,
    is_grouped_asset,
    NULLIF(TRIM(asset_category), '') AS asset_category,
    NULLIF(TRIM(asset_naming_series), '') AS asset_naming_series,
    over_delivery_receipt_allowance,
    over_billing_allowance,
    NULLIF(TRIM(image), '') AS image,
    NULLIF(TRIM(description), '') AS description,
    NULLIF(TRIM(brand), '') AS brand,
    shelf_life_in_days,
    end_of_life,
    NULLIF(TRIM(default_material_request_type), '') AS default_material_request_type,
    NULLIF(TRIM(valuation_method), '') AS valuation_method,
    NULLIF(TRIM(warranty_period), '') AS warranty_period,
    weight_per_unit,
    NULLIF(TRIM(weight_uom), '') AS weight_uom,
    allow_negative_stock,
    has_batch_no,
    create_new_batch,
    NULLIF(TRIM(batch_number_series), '') AS batch_number_series,
    has_expiry_date,
    retain_sample,
    sample_quantity,
    has_serial_no,
    NULLIF(TRIM(serial_no_series), '') AS serial_no_series,
    NULLIF(TRIM(variant_of), '') AS variant_of,
    NULLIF(TRIM(variant_based_on), '') AS variant_based_on,
    enable_deferred_expense,
    no_of_months_exp,
    enable_deferred_revenue,
    no_of_months,
    NULLIF(TRIM(purchase_uom), '') AS purchase_uom,
    min_order_qty,
    safety_stock,
    is_purchase_item,
    lead_time_days,
    last_purchase_rate,
    is_customer_provided_item,
    NULLIF(TRIM(customer), '') AS customer,
    delivered_by_supplier,
    NULLIF(TRIM(country_of_origin), '') AS country_of_origin,
    NULLIF(TRIM(customs_tariff_number), '') AS customs_tariff_number,
    NULLIF(TRIM(sales_uom), '') AS sales_uom,
    grant_commission,
    is_sales_item,
    max_discount,
    inspection_required_before_purchase,
    NULLIF(TRIM(quality_inspection_template), '') AS quality_inspection_template,
    inspection_required_before_delivery,
    include_item_in_manufacturing,
    is_sub_contracted_item,
    NULLIF(TRIM(default_bom), '') AS default_bom,
    NULLIF(TRIM(customer_code), '') AS customer_code,
    NULLIF(TRIM(default_item_manufacturer), '') AS default_item_manufacturer,
    NULLIF(TRIM(default_manufacturer_part_no), '') AS default_manufacturer_part_no,
    total_projected_qty,
    NULLIF(TRIM(_user_tags), '') AS _user_tags,
    NULLIF(TRIM(_comments), '') AS _comments,
    NULLIF(TRIM(_assign), '') AS _assign,
    NULLIF(TRIM(_liked_by), '') AS _liked_by,
    NULLIF(TRIM(kfa_code), '') AS kfa_code,
    NULLIF(TRIM(kfa_display), '') AS kfa_display,
    NULLIF(TRIM(satusehat_id), '') AS satusehat_id
FROM bronze.tabItem
QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY modified DESC) = 1
