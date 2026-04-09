import duckdb
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


def run_demo(file_path: str = "/home/brfrancis/sc-toolkit/cdr_data_warehouse/data/Indico_output_example.json", db_path: str = "cdr_demo.duckdb") -> str:
    buffer = StringIO()
    with redirect_stdout(buffer):
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Could not find: {file_path}")

        con = duckdb.connect(db_path)
        con.execute("PRAGMA enable_progress_bar;")

        with open(file_path, "r", encoding="utf-8") as f:
            raw_json = f.read()

        con.execute("""
CREATE OR REPLACE TABLE bronze_raw (
    source_file VARCHAR,
    raw_json JSON
);
""")

        con.execute("DELETE FROM bronze_raw;")
        con.execute(
            "INSERT INTO bronze_raw VALUES (?, ?::JSON)",
            [file_path, raw_json]
        )

        con.execute("""
CREATE OR REPLACE TABLE silver_field_level AS
WITH submission_files AS (
    SELECT
        b.source_file,
        sr.value AS submission_json
    FROM bronze_raw b,
    LATERAL json_each(json_extract(b.raw_json, '$.submission_results')) sr
),
model_groups AS (
    SELECT
        source_file,
        submission_json,
        mg.key AS model_group_id,
        mg.value AS model_group_json
    FROM submission_files,
    LATERAL json_each(json_extract(submission_json, '$.model_results.ORIGINAL')) mg
),
fields AS (
    SELECT
        source_file,
        submission_json,
        model_group_id,
        f.key AS field_array_index,
        f.value AS field_json
    FROM model_groups,
    LATERAL json_each(model_group_json) f
),
groupings AS (
    SELECT
        source_file,
        submission_json,
        model_group_id,
        field_array_index,
        field_json,
        g.value AS grouping_json
    FROM fields
    LEFT JOIN LATERAL json_each(
        COALESCE(json_extract(field_json, '$.groupings'), '[]'::JSON)
    ) g ON TRUE
)
SELECT
    source_file,
    json_extract_string(submission_json, '$.input_filename')              AS input_filename,
    CAST(json_extract_string(submission_json, '$.submissionfile_id') AS BIGINT) AS submissionfile_id,

    model_group_id,
    CASE model_group_id
        WHEN '6103' THEN 'Submission'
        WHEN '6104' THEN 'Location'
        WHEN '6108' THEN 'Claims'
        WHEN '6110' THEN 'Business Activity'
        WHEN '5485' THEN 'Broker'
        WHEN '5486' THEN 'Insured'
        ELSE model_group_id
    END AS model_group_name,

    CAST(field_array_index AS INTEGER)                                   AS field_array_index,
    json_extract_string(field_json, '$.label')                           AS label,
    json_extract_string(field_json, '$.text')                            AS extracted_text,
    json_extract_string(field_json, '$.location_type')                   AS location_type,

    json_extract_string(field_json, '$.normalized.text')                 AS normalized_text,
    json_extract_string(field_json, '$.normalized.formatted')            AS normalized_formatted,
    json_extract_string(field_json, '$.normalized.status')               AS normalized_status,
    json_extract_string(field_json, '$.normalized.structured.option')    AS normalized_option,

    TRY_CAST(json_extract_string(field_json, '$.spans[0].page_num') AS INTEGER) AS page_num,
    TRY_CAST(json_extract_string(field_json, '$.spans[0].start') AS INTEGER)    AS span_start,
    TRY_CAST(json_extract_string(field_json, '$.spans[0].end') AS INTEGER)      AS span_end,

    json_extract_string(grouping_json, '$.group_name')                   AS group_name,
    TRY_CAST(json_extract_string(grouping_json, '$.group_index') AS INTEGER) AS group_index,
    json_extract_string(grouping_json, '$.group_id')                     AS group_id,

    field_json
FROM groupings;
""")

        con.execute("""
CREATE OR REPLACE TABLE silver_submission AS
SELECT
    source_file,
    input_filename,
    submissionfile_id,

    MAX(CASE WHEN label = 'Submission Type'      THEN COALESCE(normalized_formatted, extracted_text) END) AS submission_type,
    MAX(CASE WHEN label = 'Product'              THEN COALESCE(normalized_formatted, extracted_text) END) AS product,
    MAX(CASE WHEN label = 'Response By'          THEN COALESCE(normalized_formatted, extracted_text) END) AS response_by,
    MAX(CASE WHEN label = 'Received On'          THEN COALESCE(normalized_formatted, extracted_text) END) AS received_on,
    MAX(CASE WHEN label = 'Renewal Due On'       THEN COALESCE(normalized_formatted, extracted_text) END) AS renewal_due_on,
    MAX(CASE WHEN label = 'Inception Date'       THEN COALESCE(normalized_formatted, extracted_text) END) AS inception_date,
    MAX(CASE WHEN label = 'Expiry Date'          THEN COALESCE(normalized_formatted, extracted_text) END) AS expiry_date,
    MAX(CASE WHEN label = 'Target Premium'       THEN TRY_CAST(COALESCE(normalized_formatted, extracted_text) AS DOUBLE) END) AS target_premium,
    MAX(CASE WHEN label = 'Number of Locations'  THEN TRY_CAST(COALESCE(normalized_formatted, extracted_text) AS INTEGER) END) AS number_of_locations,
    MAX(CASE WHEN label = 'TIV'                  THEN TRY_CAST(COALESCE(normalized_formatted, extracted_text) AS DOUBLE) END) AS total_tiv
FROM silver_field_level
WHERE model_group_id = '6103'
GROUP BY 1,2,3;
""")

        con.execute("""
CREATE OR REPLACE TABLE silver_insured AS
SELECT
    source_file,
    input_filename,
    submissionfile_id,

    MAX(CASE WHEN label = 'Insured Name'
             THEN COALESCE(normalized_formatted, extracted_text) END) AS insured_name,

    MAX(CASE WHEN label = 'Insured Primary Industry SIC code'
             THEN COALESCE(normalized_formatted, normalized_option, extracted_text) END) AS insured_primary_industry
FROM silver_field_level
WHERE model_group_id = '5486'
GROUP BY 1,2,3;
""")

        con.execute("""
CREATE OR REPLACE TABLE silver_locations AS
SELECT
    source_file,
    input_filename,
    submissionfile_id,
    group_index AS location_index,

    MAX(CASE WHEN label = 'Address Line 1'              THEN COALESCE(normalized_formatted, extracted_text) END) AS address_line_1,
    MAX(CASE WHEN label = 'City'                        THEN COALESCE(normalized_formatted, extracted_text) END) AS city,
    MAX(CASE WHEN label = 'Post Code'                   THEN COALESCE(normalized_formatted, extracted_text) END) AS post_code,
    MAX(CASE WHEN label = 'Occupancy Type'              THEN COALESCE(normalized_option, normalized_formatted, extracted_text) END) AS occupancy_type,
    MAX(CASE WHEN label = 'Buildings TIV'               THEN TRY_CAST(COALESCE(normalized_formatted, extracted_text) AS DOUBLE) END) AS buildings_tiv,
    MAX(CASE WHEN label = 'Business Interruption TIV'   THEN TRY_CAST(COALESCE(normalized_formatted, extracted_text) AS DOUBLE) END) AS business_interruption_tiv,
    MAX(CASE WHEN label = 'Stock TIV'                   THEN TRY_CAST(COALESCE(normalized_formatted, extracted_text) AS DOUBLE) END) AS stock_tiv,
    MAX(CASE WHEN label = 'Year Built'                  THEN TRY_CAST(COALESCE(normalized_formatted, extracted_text) AS INTEGER) END) AS year_built,
    MAX(CASE WHEN label = 'Construction Class'          THEN COALESCE(normalized_option, normalized_formatted, extracted_text) END) AS construction_class
FROM silver_field_level
WHERE model_group_id = '6104'
  AND group_name = 'Locations'
GROUP BY 1,2,3,4;
""")

        con.execute("""
CREATE OR REPLACE TABLE silver_claims AS
SELECT
    source_file,
    input_filename,
    submissionfile_id,
    group_index AS claim_index,

    MAX(CASE WHEN label = 'Date of Loss'    THEN COALESCE(normalized_formatted, extracted_text) END) AS date_of_loss,
    MAX(CASE WHEN label = 'Included'        THEN COALESCE(normalized_option, normalized_formatted, extracted_text) END) AS included,
    MAX(CASE WHEN label = 'Incurred'        THEN COALESCE(normalized_formatted, extracted_text) END) AS incurred,
    MAX(CASE WHEN label = 'Loss Type'       THEN COALESCE(normalized_formatted, extracted_text) END) AS loss_type,
    MAX(CASE WHEN label = 'Name'            THEN COALESCE(normalized_formatted, extracted_text) END) AS claim_name,
    MAX(CASE WHEN label = 'Outstanding'     THEN COALESCE(normalized_formatted, extracted_text) END) AS outstanding,
    MAX(CASE WHEN label = 'Paid'            THEN TRY_CAST(COALESCE(normalized_formatted, extracted_text) AS DOUBLE) END) AS paid,
    MAX(CASE WHEN label = 'Peril'           THEN COALESCE(normalized_option, normalized_formatted, extracted_text) END) AS peril
FROM silver_field_level
WHERE model_group_id = '6108'
  AND group_name = 'Claims'
GROUP BY 1,2,3,4;
""")

        con.execute("""
CREATE OR REPLACE TABLE silver_exposures AS
SELECT
    source_file,
    input_filename,
    submissionfile_id,
    group_index AS exposure_index,

    MAX(CASE WHEN label = 'Name'               THEN COALESCE(normalized_formatted, extracted_text) END) AS exposure_name,
    MAX(CASE WHEN label = 'Activity Reference' THEN COALESCE(normalized_formatted, extracted_text) END) AS activity_reference,
    MAX(CASE WHEN label = 'Exposure Type'      THEN COALESCE(normalized_option, normalized_formatted, extracted_text) END) AS exposure_type,
    MAX(CASE WHEN label = 'Exposure Period'    THEN COALESCE(normalized_formatted, extracted_text) END) AS exposure_period,
    MAX(CASE WHEN label = 'Exposure Amount'    THEN TRY_CAST(COALESCE(normalized_formatted, extracted_text) AS DOUBLE) END) AS exposure_amount,
    MAX(CASE WHEN label = 'Geography'          THEN COALESCE(normalized_option, normalized_formatted, extracted_text) END) AS geography,
    MAX(CASE WHEN label = 'Split Percent'      THEN TRY_CAST(COALESCE(normalized_formatted, extracted_text) AS DOUBLE) END) AS split_percent
FROM silver_field_level
WHERE model_group_id = '6110'
  AND group_name = 'Exposures'
GROUP BY 1,2,3,4;
""")

        con.execute("""
CREATE OR REPLACE VIEW gold_cdr_locations AS
SELECT
    s.input_filename,
    s.submissionfile_id,

    i.insured_name,
    i.insured_primary_industry,

    s.submission_type,
    s.product,
    s.received_on,
    s.inception_date,
    s.expiry_date,
    s.target_premium,
    s.total_tiv,

    l.location_index,
    l.address_line_1,
    l.city,
    l.post_code,
    l.occupancy_type,
    l.buildings_tiv,
    l.business_interruption_tiv,
    l.stock_tiv,
    l.year_built,
    l.construction_class
FROM silver_submission s
LEFT JOIN silver_insured i
  ON s.source_file = i.source_file
 AND s.submissionfile_id = i.submissionfile_id
LEFT JOIN silver_locations l
  ON s.source_file = l.source_file
 AND s.submissionfile_id = l.submissionfile_id;
""")

        con.execute("""
CREATE OR REPLACE VIEW gold_cdr_claims AS
SELECT
    s.input_filename,
    s.submissionfile_id,
    i.insured_name,
    c.claim_index,
    c.date_of_loss,
    c.claim_name,
    c.peril,
    c.paid,
    c.incurred,
    c.outstanding,
    c.included
FROM silver_submission s
LEFT JOIN silver_insured i
  ON s.source_file = i.source_file
 AND s.submissionfile_id = i.submissionfile_id
LEFT JOIN silver_claims c
  ON s.source_file = c.source_file
 AND s.submissionfile_id = c.submissionfile_id;
""")

        print("\n--- bronze_raw ---")
        print(con.execute("SELECT source_file, json_type(raw_json) AS raw_json_type FROM bronze_raw").fetchdf())

        print("\n--- silver_submission ---")
        print(con.execute("SELECT * FROM silver_submission").fetchdf())

        print("\n--- silver_insured ---")
        print(con.execute("SELECT * FROM silver_insured").fetchdf())

        print("\n--- silver_locations ---")
        print(con.execute("""
    SELECT *
    FROM silver_locations
    ORDER BY location_index
""").fetchdf())

        print("\n--- silver_claims ---")
        print(con.execute("""
    SELECT *
    FROM silver_claims
    ORDER BY claim_index
""").fetchdf())

        print("\n--- silver_exposures ---")
        print(con.execute("""
    SELECT *
    FROM silver_exposures
    ORDER BY exposure_index
""").fetchdf())

        print("\n--- gold_cdr_locations ---")
        print(con.execute("""
    SELECT *
    FROM gold_cdr_locations
    ORDER BY location_index
""").fetchdf())

        print("\n--- gold_cdr_claims ---")
        print(con.execute("""
    SELECT *
    FROM gold_cdr_claims
    ORDER BY claim_index
""").fetchdf())

        con.close()

    return buffer.getvalue()
