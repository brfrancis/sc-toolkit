"""
CDR v3.2 field schema definition.
Maps Indico extraction field names to canonical CDR field names and types.
Extend this as additional CDR field groups are implemented.
"""

CDR_FIELD_MAP = {
    # Risk identification
    "insured_name":         {"cdr_field": "InsuredName",        "type": "string",  "required": True},
    "umr":                  {"cdr_field": "UMR",                "type": "string",  "required": True},
    "inception_date":       {"cdr_field": "InceptionDate",      "type": "date",    "required": True},
    "expiry_date":          {"cdr_field": "ExpiryDate",         "type": "date",    "required": True},

    # Coverage
    "total_insured_value":  {"cdr_field": "TotalInsuredValue",  "type": "numeric", "required": False},
    "premium":              {"cdr_field": "Premium",            "type": "numeric", "required": True},
    "deductible":           {"cdr_field": "Deductible",         "type": "numeric", "required": False},
    "limit":                {"cdr_field": "Limit",              "type": "numeric", "required": True},
    "currency":             {"cdr_field": "Currency",           "type": "string",  "required": True},

    # Risk location
    "country":              {"cdr_field": "RiskCountry",        "type": "string",  "required": False},
    "territory":            {"cdr_field": "RiskTerritory",      "type": "string",  "required": False},

    # Broker / market
    "broker_name":          {"cdr_field": "BrokerName",         "type": "string",  "required": False},
    "broker_reference":     {"cdr_field": "BrokerReference",    "type": "string",  "required": False},
    "class_of_business":    {"cdr_field": "ClassOfBusiness",    "type": "string",  "required": True},
}
