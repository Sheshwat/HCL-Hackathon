"""
generate_source_data.py
=======================
Generates all 12 source CSV files for the Insurance Policy pipeline.
  4 files × 3 days = 12 files
  day0 = full initial load
  day1 = incremental updates (new records + changes)
  day2 = further incremental updates

Each file has a Region column (EAST/WEST/NORTH/SOUTH).
Output → source_data/
"""

import csv
import os
import random
from datetime import date, timedelta

random.seed(42)
OUT = os.path.join(os.path.dirname(__file__), "..", "source_data")
os.makedirs(OUT, exist_ok=True)

REGIONS     = ["EAST", "WEST", "NORTH", "SOUTH"]
SEGMENTS    = ["Consumer", "Corporate", "SME"]
GENDERS     = ["Male", "Female"]
MARITAL_S   = ["Single", "Married", "Divorced", "Widowed"]
POL_TERMS   = ["Monthly", "Quarterly", "Annual"]
POL_TYPES   = {
    "PT001": {"name": "Auto",      "desc": "Auto insurance policy"},
    "PT002": {"name": "WholeLife", "desc": "Whole life insurance policy"},
    "PT003": {"name": "Term",      "desc": "Term life insurance policy"},
    "PT004": {"name": "Health",    "desc": "Health insurance policy"},
    "PT005": {"name": "Home",      "desc": "Home insurance policy"},
}
TITLES      = ["Mr.", "Mrs.", "Ms.", "Dr.", "Professor"]
FIRST_NAMES = ["Aaron","Bonnie","Charles","Diana","Edward","Fiona","Gwendolyn",
               "Henry","Irene","James","Karen","Liam","Megan","Nathan","Olivia",
               "Patrick","Quinn","Rachel","Samuel","Tina","Ursula","Victor",
               "Wendy","Xander","Yvonne","Zachary","Allison","Brian","Catherine"]
LAST_NAMES  = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller",
               "Davis","Wilson","Anderson","Taylor","Thomas","Jackson","White",
               "Harris","Martin","Thompson","Potter","Kirby","Tyson","Dillon"]
COUNTRIES   = ["United States"]
REGION_STATES = {
    "EAST":  ["New York","New Jersey","Massachusetts","Pennsylvania","Connecticut"],
    "WEST":  ["California","Oregon","Washington","Nevada","Arizona"],
    "NORTH": ["Minnesota","Wisconsin","Michigan","Illinois","Ohio"],
    "SOUTH": ["Texas","Florida","Georgia","Alabama","Louisiana"],
}
REGION_CITIES = {
    "EAST":  ["New York City","Boston","Philadelphia","Newark","Hartford"],
    "WEST":  ["Los Angeles","San Francisco","Seattle","Las Vegas","Phoenix"],
    "NORTH": ["Chicago","Detroit","Minneapolis","Milwaukee","Cleveland"],
    "SOUTH": ["Houston","Miami","Atlanta","Dallas","New Orleans"],
}

def rand_date(start_year=1955, end_year=2000):
    start = date(start_year, 1, 1)
    end   = date(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))

def rand_policy_date(start_year=2005, end_year=2023):
    start = date(start_year, 1, 1)
    end   = date(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))

def postal_code():
    return str(random.randint(10000, 99999))

# ── Build master customer list ──────────────────────────────────────────────
customers = []
for cid in range(1, 701):          # 700 customers
    region  = random.choice(REGIONS)
    fname   = random.choice(FIRST_NAMES)
    lname   = random.choice(LAST_NAMES)
    title   = random.choice(TITLES)
    dob     = rand_date(1950, 2000)
    eff_st  = rand_date(2000, 2015)
    eff_end = ""                    # blank = still active
    marital = random.choice(MARITAL_S)
    customers.append({
        "Customer_ID":        cid,
        "Customer_Title":     title,
        "Customer_First_Name":fname,
        "Customer_Last_Name": lname,
        "Customer_Segment":   random.choice(SEGMENTS),
        "Marital_Status":     marital,
        "Gender":             random.choice(GENDERS),
        "DOB":                dob.strftime("%Y-%m-%d"),
        "Effective_Start_Dt": eff_st.strftime("%Y-%m-%d"),
        "Effective_End_Dt":   eff_end,
        "Region":             region,
    })

# Override a few well-known customers to match sample outputs
customers[2]["Customer_First_Name"]  = "Bonnie"
customers[2]["Customer_Last_Name"]   = "Potter"
customers[2]["Customer_Title"]       = "Mister."
customers[2]["Customer_ID"]          = 3
customers[13]["Customer_First_Name"] = "Gwendolyn"
customers[13]["Customer_Last_Name"]  = "Tyson"
customers[13]["Customer_Title"]      = "Mr."
customers[13]["Customer_ID"]         = 14
customers[666]["Customer_First_Name"]= "Allison"
customers[666]["Customer_Last_Name"] = "Kirby"
customers[666]["Customer_Title"]     = "Professor"
customers[666]["Customer_ID"]        = 667
customers.append({   # SCD customer 1354
    "Customer_ID":        1354,
    "Customer_Title":     "Mr.",
    "Customer_First_Name":"AARON",
    "Customer_Last_Name": "DILLON",
    "Customer_Segment":   "Consumer",
    "Marital_Status":     "Single",
    "Gender":             "Male",
    "DOB":                "1985-02-15",
    "Effective_Start_Dt": "1997-02-05",
    "Effective_End_Dt":   "2024-04-12",
    "Region":             "EAST",
})

# ── Build master policy list ────────────────────────────────────────────────
policies = []
pol_id_counter = 10000
for cid_idx, cust in enumerate(customers[:700]):
    n_pols = random.randint(1, 3)
    for _ in range(n_pols):
        pol_id_counter += 1
        pt_key  = random.choice(list(POL_TYPES.keys()))
        pt      = POL_TYPES[pt_key]
        pstart  = rand_policy_date(2005, 2020)
        term    = random.choice(POL_TERMS)
        if term == "Monthly":
            pend = pstart + timedelta(days=365)
        elif term == "Quarterly":
            pend = pstart + timedelta(days=365 * 2)
        else:
            pend = pstart + timedelta(days=365 * 5)
        premium    = random.choice([5000, 7500, 10000, 12500, 15000, 20000, 25000])
        total_amt  = random.choice([200000, 300000, 400000, 500000, 600000, 800000, 1000000])
        paid_till  = pstart + timedelta(days=random.randint(30, 500))
        next_prem  = paid_till + timedelta(days=30)
        policies.append({
            "Policy_Type_Id":   pt_key,
            "Policy_Type":      pt["name"],
            "Policy_Type_Desc": pt["desc"],
            "Policy_Id":        pol_id_counter,
            "Policy_Name":      f"{pt['name']} Policy {pol_id_counter}",
            "Customer_ID":      cust["Customer_ID"],
            "Premium_Amt":      premium,
            "Policy_Term":      term,
            "Policy_Start_Dt":  pstart.strftime("%Y-%m-%d"),
            "Policy_End_Dt":    pend.strftime("%Y-%m-%d"),
            "Next_Premium_Dt":  next_prem.strftime("%Y-%m-%d"),
            "Actual_Premium_Paid_Dt": paid_till.strftime("%Y-%m-%d"),
            "Total_Policy_Amt": total_amt,
            "Premium_Amt_Paid_TillDate": round(premium * random.uniform(0.2, 0.9), 2),
            "Region":           cust["Region"],
        })

# Patch specific customers for sample queries
# Customer 3 — Quarterly, East+West, 2012
for p in policies:
    if p["Customer_ID"] == 3:
        p["Policy_Term"]      = "Quarterly"
        p["Policy_Start_Dt"]  = "2012-01-02"
        p["Total_Policy_Amt"] = 800000
        p["Region"]           = "EAST"
        break
# Customer 14 — All regions
for p in policies:
    if p["Customer_ID"] == 14:
        p["Total_Policy_Amt"] = 900000
        break
# Customer 667 — Auto
for p in policies:
    if p["Customer_ID"] == 667:
        p["Policy_Type"]      = "Auto"
        p["Policy_Type_Id"]   = "PT001"
        p["Total_Policy_Amt"] = 600000
        break

# ── Build address list ──────────────────────────────────────────────────────
addresses = []
for cust in customers[:700]:
    region = cust["Region"]
    addresses.append({
        "Customer_ID":   cust["Customer_ID"],
        "Country":       "United States",
        "Region":        region,
        "State":         random.choice(REGION_STATES[region]),
        "City":          random.choice(REGION_CITIES[region]),
        "Postal_Code":   postal_code(),
    })

# ── Build transaction list ──────────────────────────────────────────────────
transactions = []
for pol in policies:
    n_tx = random.randint(1, 5)
    for i in range(n_tx):
        tx_dt = date.fromisoformat(pol["Policy_Start_Dt"]) + timedelta(days=30 * i)
        transactions.append({
            "Policy_Id":              pol["Policy_Id"],
            "Customer_ID":            pol["Customer_ID"],
            "Premium_Amt":            pol["Premium_Amt"],
            "Total_Policy_Amt":       pol["Total_Policy_Amt"],
            "Premium_Amt_Paid_TillDate": pol["Premium_Amt_Paid_TillDate"],
            "Next_Premium_Dt":        pol["Next_Premium_Dt"],
            "Actual_Premium_Paid_Dt": tx_dt.strftime("%Y-%m-%d"),
            "Region":                 pol["Region"],
        })


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  Written: {os.path.basename(path)}  ({len(rows)} rows)")


# ═══════════════════════════════════════════════════════════════════
# DAY 0  — full initial load (all 700 customers, first 500 policies)
# ═══════════════════════════════════════════════════════════════════
print("\n=== Generating DAY 0 ===")
write_csv(f"{OUT}/day0_customers.csv",    customers[:700],
          ["Customer_ID","Customer_Title","Customer_First_Name","Customer_Last_Name",
           "Customer_Segment","Marital_Status","Gender","DOB",
           "Effective_Start_Dt","Effective_End_Dt","Region"])
write_csv(f"{OUT}/day0_policies.csv",     policies[:800],
          ["Policy_Type_Id","Policy_Type","Policy_Type_Desc","Policy_Id","Policy_Name",
           "Customer_ID","Premium_Amt","Policy_Term","Policy_Start_Dt","Policy_End_Dt",
           "Next_Premium_Dt","Actual_Premium_Paid_Dt","Total_Policy_Amt",
           "Premium_Amt_Paid_TillDate","Region"])
write_csv(f"{OUT}/day0_address.csv",      addresses[:700],
          ["Customer_ID","Country","Region","State","City","Postal_Code"])
write_csv(f"{OUT}/day0_transactions.csv", transactions[:1500],
          ["Policy_Id","Customer_ID","Premium_Amt","Total_Policy_Amt",
           "Premium_Amt_Paid_TillDate","Next_Premium_Dt","Actual_Premium_Paid_Dt","Region"])

# ═══════════════════════════════════════════════════════════════════
# DAY 1  — incremental: new customers 701-750, marital status changes,
#          policy type changes, new transactions
# ═══════════════════════════════════════════════════════════════════
print("\n=== Generating DAY 1 ===")
# New customers
new_custs_d1 = []
for cid in range(701, 751):
    region = random.choice(REGIONS)
    new_custs_d1.append({
        "Customer_ID":        cid,
        "Customer_Title":     random.choice(TITLES),
        "Customer_First_Name":random.choice(FIRST_NAMES),
        "Customer_Last_Name": random.choice(LAST_NAMES),
        "Customer_Segment":   random.choice(SEGMENTS),
        "Marital_Status":     random.choice(MARITAL_S),
        "Gender":             random.choice(GENDERS),
        "DOB":                rand_date(1970, 2000).strftime("%Y-%m-%d"),
        "Effective_Start_Dt": "2024-01-15",
        "Effective_End_Dt":   "",
        "Region":             region,
    })
# SCD marital status change for customer 1354 (Married)
scd_cust_d1 = {
    "Customer_ID":        1354,
    "Customer_Title":     "Mr.",
    "Customer_First_Name":"Aaron",
    "Customer_Last_Name": "Dillon",
    "Customer_Segment":   "Consumer",
    "Marital_Status":     "Married",
    "Gender":             "Male",
    "DOB":                "1985-02-15",
    "Effective_Start_Dt": "2024-04-12",
    "Effective_End_Dt":   "2024-04-12",
    "Region":             "EAST",
}
write_csv(f"{OUT}/day1_customers.csv", new_custs_d1 + [scd_cust_d1],
          ["Customer_ID","Customer_Title","Customer_First_Name","Customer_Last_Name",
           "Customer_Segment","Marital_Status","Gender","DOB",
           "Effective_Start_Dt","Effective_End_Dt","Region"])

# Policy changes — some customers switch policy type
changed_policies = []
for p in policies[800:1000]:
    old_pt = p["Policy_Type_Id"]
    new_pt = random.choice([k for k in POL_TYPES if k != old_pt])
    changed_policies.append({**p,
        "Policy_Type_Id":   new_pt,
        "Policy_Type":      POL_TYPES[new_pt]["name"],
        "Policy_Type_Desc": POL_TYPES[new_pt]["desc"],
    })
write_csv(f"{OUT}/day1_policies.csv", changed_policies,
          ["Policy_Type_Id","Policy_Type","Policy_Type_Desc","Policy_Id","Policy_Name",
           "Customer_ID","Premium_Amt","Policy_Term","Policy_Start_Dt","Policy_End_Dt",
           "Next_Premium_Dt","Actual_Premium_Paid_Dt","Total_Policy_Amt",
           "Premium_Amt_Paid_TillDate","Region"])

new_addr_d1 = [{**a, "Customer_ID": cid}
               for cid, a in zip(range(701,751), addresses[:50])]
write_csv(f"{OUT}/day1_address.csv", new_addr_d1,
          ["Customer_ID","Country","Region","State","City","Postal_Code"])

write_csv(f"{OUT}/day1_transactions.csv", transactions[1500:2200],
          ["Policy_Id","Customer_ID","Premium_Amt","Total_Policy_Amt",
           "Premium_Amt_Paid_TillDate","Next_Premium_Dt","Actual_Premium_Paid_Dt","Region"])

# ═══════════════════════════════════════════════════════════════════
# DAY 2  — incremental: more customers 751-800, further SCD,
#          premium payments, new policies
# ═══════════════════════════════════════════════════════════════════
print("\n=== Generating DAY 2 ===")
new_custs_d2 = []
for cid in range(751, 801):
    region = random.choice(REGIONS)
    new_custs_d2.append({
        "Customer_ID":        cid,
        "Customer_Title":     random.choice(TITLES),
        "Customer_First_Name":random.choice(FIRST_NAMES),
        "Customer_Last_Name": random.choice(LAST_NAMES),
        "Customer_Segment":   random.choice(SEGMENTS),
        "Marital_Status":     random.choice(MARITAL_S),
        "Gender":             random.choice(GENDERS),
        "DOB":                rand_date(1970, 2000).strftime("%Y-%m-%d"),
        "Effective_Start_Dt": "2024-02-20",
        "Effective_End_Dt":   "",
        "Region":             region,
    })
# SCD: customer 1354 now Divorced
scd_cust_d2 = {
    "Customer_ID":        1354,
    "Customer_Title":     "Mr.",
    "Customer_First_Name":"Aaron",
    "Customer_Last_Name": "Dillon",
    "Customer_Segment":   "Consumer",
    "Marital_Status":     "Divorced",
    "Gender":             "Male",
    "DOB":                "1985-02-15",
    "Effective_Start_Dt": "2024-04-13",
    "Effective_End_Dt":   "2099-12-31",
    "Region":             "EAST",
}
write_csv(f"{OUT}/day2_customers.csv", new_custs_d2 + [scd_cust_d2],
          ["Customer_ID","Customer_Title","Customer_First_Name","Customer_Last_Name",
           "Customer_Segment","Marital_Status","Gender","DOB",
           "Effective_Start_Dt","Effective_End_Dt","Region"])
write_csv(f"{OUT}/day2_policies.csv", policies[1000:1200],
          ["Policy_Type_Id","Policy_Type","Policy_Type_Desc","Policy_Id","Policy_Name",
           "Customer_ID","Premium_Amt","Policy_Term","Policy_Start_Dt","Policy_End_Dt",
           "Next_Premium_Dt","Actual_Premium_Paid_Dt","Total_Policy_Amt",
           "Premium_Amt_Paid_TillDate","Region"])
new_addr_d2 = [{**a, "Customer_ID": cid}
               for cid, a in zip(range(751,801), addresses[:50])]
write_csv(f"{OUT}/day2_address.csv", new_addr_d2,
          ["Customer_ID","Country","Region","State","City","Postal_Code"])
write_csv(f"{OUT}/day2_transactions.csv", transactions[2200:],
          ["Policy_Id","Customer_ID","Premium_Amt","Total_Policy_Amt",
           "Premium_Amt_Paid_TillDate","Next_Premium_Dt","Actual_Premium_Paid_Dt","Region"])

print("\n✅ All 12 source CSV files generated successfully in source_data/")
