from csv import DictReader, DictWriter
from tqdm import tqdm
import os
import shutil
from openfisca_uk.tools.simulation import model
import numpy as np

BENEFITS = {
    1: "DLA_SC",
    2: "DLA_M",
    3: "child_benefit",
    4: "pension_credit",
    5: "state_pension",
    6: "BSP",
    8: "AFCS",
    9: "war_pension",
    10: "SDA",
    12: "AA",
    13: "carers_allowance",
    14: "JSA",
    14.1: "JSA_contrib",
    14.2: "JSA_income",
    15: "IIDB",
    17: "incapacity_benefit",
    19: "income_support",
    21: "maternity_allowance",
    37: "guardians_allowance",
    36: "GTA",
    30: "other_benefit",
    90: "working_tax_credit",
    91: "child_tax_credit",
    92: "WTC_lump_sum",
    93: "CTC_lump_sum",
    94: "housing_benefit",
    69: "SFL_IS",
    70: "SFL_JSA",
    111: "SFL_UC",
    62: "winter_fuel_allowance",
    65: "DWP_IS",
    66: "DWP_JSA",
    110: "DWP_UC",
    24: "FG",
    22: "MG",
    60: "widows_payment",
    98: "DWP_loan",
    99: "LA_loan",
    95: "universal_credit",
    96: "PIP_DL",
    97: "PIP_M"
}

BENEFITS = {code: benefit + "_reported" for code, benefit in BENEFITS.items()}

AGES = [2, 7, 13, 18, 22, 27, 32, 37, 42, 47, 52, 57, 62, 67, 72, 77, 82, 90]

JSA_ESA_TYPES = {
    0: "income",
    1: "income",
    2: "income",
    3: "contrib",
    4: "contrib",
    5: "income",
    6: "income"
}

PERSON_FIELDNAMES = [
    "person_id",
    "benunit_id",
    "household_id",
    "role",
    "is_male",
    "is_adult",
    "is_child",
    "age",
    "is_head",
    "is_householder",
    "employee_earnings",
    "deductions",
    "self_employed_earnings",
    "pension_income",
    "total_benefits",
    "interest",
    "assets",
    "maintenance_expense",
    "misc_income",
    "JSA_contrib_eligible",
    "disabled",
    "adult_weight",
    "hours_worked",
    "actual_net_income",
    "student_loan_repayments",
    "net_income_adjustment",
    "eligible_childcare_cost",
    "SSP",
    "is_adult_1",
    "total_disability_benefits"
] + list(BENEFITS.values())

BENUNIT_FIELDNAMES = [
    "benunit_id",
    "benunit_weight",
    "external_child_maintenance"
]

HOUSEHOLD_FIELDNAMES = [
    "household_id",
    "household_weight",
    "council_tax",
    "housing_costs",
    "service_charges",
    "region"
]

AVERAGE_COUNCIL_TAX = [
    1114,
    1300,
    1486,
    1671,
    2043,
    2414,
    2786,
    3343,
    3900,
    0
]

def clean_dirs(output_dir):
    """
    Clears the output directory of any existing files.
    """
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

def exists(field):
    """
    Return true if the field is numeric.
    """
    try:
        float(field)
        return True
    except:
        return False

def safe(*backups):
    """
    Attempt to parse a text field as a numeric input.
    """
    for value in backups:
        if exists(value):
            return float(value)
    return 0

def add_up(line, *fieldnames):
    return sum(map(safe, map(lambda fieldname : line[fieldname], fieldnames)))

def weeklyise(value, period_code):
    if not exists(value) or not exists(period_code):
        return 0
    num_weeks = {
        1: 1,
        2: 2,
        3: 3,
        4: 4,
        5: 4.35,
        7: 8.7,
        8: 6.52,
        9: 5.8,
        10: 5.22,
        13: 13,
        17: 17.4,
        26: 26,
        52: 52,
        90: 0.5,
        95: 1000,
        97: 1000
    }[int(period_code)]
    return float(value) / num_weeks

def init_data(dictionary, fieldnames):
    """
    Initialise a dictionary with fieldnames and zero values.
    """
    for key in fieldnames:
        dictionary[key] = 0

def parse_file(filename, id_func, parse_func, initial_fields=[], data={}, desc=None):
    """
    Read a data file, changing a data dictionary according to specified procedures.
    """
    if desc is None:
        desc = f"Reading {filename}"
    with open(os.path.join("data", filename), encoding="utf-8") as f:
        reader = DictReader(f, fieldnames=next(f).split("\t"), delimiter="\t")
        for line in tqdm(reader, desc=desc):
            identity = id_func(line)
            if identity not in data or data[identity] is None:
                entity = {field: 0 for field in initial_fields}
            else:
                entity = data[identity]
            try:
                data[identity] = parse_func(line, entity)
            except Exception as e:
                raise e
        return data

def write_file(data, filename, fieldnames):
    """
    Write a data dictionary to a CSV file.
    """
    with open(os.path.join("output", filename), "w+", encoding="utf-8", newline="") as f:
        writer = DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in tqdm(data.values(), desc=f"Writing {filename} file"):
            for field in fieldnames:
                if field not in item:
                    item[field] = 0
            writer.writerow(item)

def person_id(line):
    return line["sernum"] + "p" + line["PERSON"]

def household_id(line):
    return line["sernum"]

def parse_adult(line, person):
    person["person_id"] = person_id(line)
    person["benunit_id"] = benunit_id(line)
    person["household_id"] = household_id(line)
    person["role"] = "adult"
    person["is_male"] = line["SEX"] == "1"
    person["is_adult"] = True
    person["is_child"] = False
    person["age"] = AGES[int(line["IAGEGR4"])]
    person["misc_income"] = safe(line["NINRINC"])
    person["student_loan_repayments"] = weeklyise(line["SLREPAMT"], line["SLREPPD"])
    person["hours_worked"] = safe(line["TOTHOURS"])
    person["disabled"] = line["DISACTA1"] == "1"
    person["adult_weight"] = float(line["GROSS4"])
    person["is_head"] = int(line["COMBID"] == "1")
    person["is_householder"] = int(line["HHOLDER"] == "1")
    person["actual_net_income"] = safe(line["NINDINC"]) - safe(line["NINRINC"])
    person["self_employed_earnings"] = safe(line["SEINCAM2"])
    person["employee_earnings"] = safe(line["INEARNS"])
    person["SSP"] = safe(line["SSPADJ"])
    person["is_adult_1"] = False
    person["total_disability_benefits"] = safe(line["INDISBEN"])
    return person

def parse_childcare(line, person):
    if line["REGISTRD"] == "1":
        person["eligible_childcare_cost"] += safe(line["CHAMT"])
    return person

def parse_child(line, person):
    person["person_id"] = person_id(line)
    person["benunit_id"] = benunit_id(line)
    person["household_id"] = household_id(line)
    person["role"] = "child"
    person["is_male"] = line["SEX"] == "1"
    person["is_adult"] = False
    person["is_child"] = True
    person["age"] = safe(line["AGE"])
    person["misc_income"] = safe(line["CHRINC"])
    person["disabled"] = line["DISACTC1"] == "1"
    person["is_adult_1"] = False
    person["total_disability_benefits"] = 0
    return person

def parse_job(line, person):
    # person["employee_earnings"] += safe(line["UGROSS"], line["GRWAGE"])
    person["deductions"] += weeklyise(add_up(line, "DEDOTH", "DEDUC1", "DEDUC2", "DEDUC3", "DEDUC4", "DEDUC5", "DEDUC6", "DEDUC7", "DEDUC8", "DEDUC9"), line["GRWAGPD"])
    return person

def parse_account(line, person):
    person["interest"] += safe(line["ACCINT"])
    return person

def parse_asset(line, person):
    person["assets"] += safe(line["HOWMUCHE"], line["HOWMUCH"])
    return person

def parse_maintenance(line, person):
    person["maintenance_expense"] += weeklyise(safe(line["MRUAMT"], line["MRAMT"]), line["MRPD"])
    return person

def parse_benefit(line, person):
    code = int(line["BENEFIT"])
    if code not in BENEFITS:
        return person
    benefit_name = BENEFITS[code]
    amount = safe(line["BENAMT"])
    if code == 30 and (line["PRES"] != "1" or int(safe(line["BENPD"])) >= 90):
        amount = 0
    elif code in [24, 22, 60]:
        amount *= 7 / 365
    elif code in [65, 66, 110] and line["VAR2"] == "1":
        amount = 0
    elif code == 14:
        JSA_type = JSA_ESA_TYPES[int(safe(line["VAR2"]))]
        benefit_name = benefit_name.replace("JSA", f"JSA_{JSA_type}")
    elif code == 54:
        ESA_type = JSA_ESA_TYPES[int(safe(line["VAR2"]))]
        benefit_name = benefit_name.replace("ESA", f"ESA_{ESA_type}")
    elif code == 62:
        amount /= 52
    person["total_benefits"] += amount
    person[benefit_name] += amount
    return person

def parse_pension(line, person):
    person["pension_income"] += safe(line["PENPAY"]) + safe(line["PTAMT"])
    return person

def benunit_id(line):
    return line["sernum"] + "b" + line["BENUNIT"]

def parse_benunit(line, benunit):
    benunit["benunit_id"] = benunit_id(line)
    benunit["benunit_weight"] = float(line["GROSS4"])
    return benunit

def parse_household(line, household):
    household["household_id"] = household_id(line)
    band = int(safe(line["CTBAND"]))
    household["council_tax"] = safe(line["CTANNUAL"], AVERAGE_COUNCIL_TAX[band - 1]) / 52
    household["housing_costs"] = safe(line["GBHSCOST"]) + safe(line["NIHSCOST"])
    household["service_charges"] = 0
    household["household_weight"] = float(line["GROSS4"])
    household["region"] = safe(line["GVTREGNO"])
    return household

def parse_extchild(line, benunit):
    benunit["external_child_maintenance"] = weeklyise(line["NHHAMT"], line["NHHPD"])
    return benunit

def adjust_net_income():
    sim = model(data_dir="output")
    simulated_net_income = sim.calculate("net_income", "2020-10")
    person_data = {}
    with open("output\\person.csv") as f:
        next(f)
        reader = DictReader(f, fieldnames=PERSON_FIELDNAMES)
        for row in tqdm(reader, desc="Reading person.csv"):
            person_data[row["person_id"]] = row
    actual_net_income = np.array([float(person["actual_net_income"]) for person in person_data.values()])
    error = simulated_net_income - actual_net_income
    adjustment = np.where(np.abs(error) > 200, -error, 0)
    person_ids = list(person_data.keys())
    for i, person_id in tqdm(zip(range(len(person_ids)), person_ids), desc="Storing net income adjustments"):
        person_data[person_id]["net_income_adjustment"] = adjustment[i]
    with open("output\\person.csv", "w+", encoding="utf-8", newline="") as f:
        writer = DictWriter(f, fieldnames=PERSON_FIELDNAMES)
        writer.writeheader()
        for person in person_data.values():
            writer.writerow(person)

def assign_missing_benunit_heads(data):
    benunit_heads = {}
    person_ids = list(data.keys())
    for i in range(len(person_ids)):
        if data[person_ids[i]]["benunit_id"] not in benunit_heads:
            data[person_ids[i]]["is_adult_1"] = True
            benunit_heads[data[person_ids[i]]["benunit_id"]] = data[person_ids[i]]["person_id"]
        else:
            data[person_ids[i]]["is_adult_1"] = False
    return data

def get_person_data():
    """
    Return a dictionary of person-level data.
    """
    person_data = parse_file("adult.tab", person_id, parse_adult, initial_fields=PERSON_FIELDNAMES, data={})
    person_data = assign_missing_benunit_heads(person_data)
    person_data = parse_file("child.tab", person_id, parse_child, initial_fields=PERSON_FIELDNAMES, data=person_data)
    person_data = parse_file("job.tab", person_id, parse_job, initial_fields=PERSON_FIELDNAMES, data=person_data)
    person_data = parse_file("pension.tab", person_id, parse_pension, initial_fields=PERSON_FIELDNAMES, data=person_data)
    person_data = parse_file("benefits.tab", person_id, parse_benefit, initial_fields=PERSON_FIELDNAMES, data=person_data)
    person_data = parse_file("accounts.tab", person_id, parse_account, initial_fields=PERSON_FIELDNAMES, data=person_data)
    person_data = parse_file("assets.tab", person_id, parse_asset, initial_fields=PERSON_FIELDNAMES, data=person_data)
    person_data = parse_file("maint.tab", person_id, parse_maintenance, initial_fields=PERSON_FIELDNAMES, data=person_data)
    person_data = parse_file("chldcare.tab", person_id, parse_childcare, initial_fields=PERSON_FIELDNAMES, data=person_data)
    write_file(person_data, "person.csv", PERSON_FIELDNAMES)
    benunit_data = parse_file("benunit.tab", benunit_id, parse_benunit, initial_fields=BENUNIT_FIELDNAMES, data={})
    benunit_data = parse_file("extchild.tab", benunit_id, parse_extchild, initial_fields=BENUNIT_FIELDNAMES, data=benunit_data)
    write_file(benunit_data, "benunit.csv", BENUNIT_FIELDNAMES)
    household_data = parse_file("househol.tab", household_id, parse_household, initial_fields=HOUSEHOLD_FIELDNAMES, data={})
    write_file(household_data, "household.csv", HOUSEHOLD_FIELDNAMES)

clean_dirs("output")
get_person_data()