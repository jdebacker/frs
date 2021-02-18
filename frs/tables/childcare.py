from frs.table_utils import *


def parse_childcare(line, person):
    person["childcare_cost"] += yearly(line["CHAMT"])
    person["weekly_childcare_hours"] += yearly(line["CHHR"])
    person["employer_provided_childcare_cost"] += (
        safe(line["EMPLPROV"]) * person["childcare_cost"]
    )
    person["has_registered_childcare"] = safe(line["REGISTRD"]) == 1
    return person


CHILDCARE_FIELDNAMES = [
    "childcare_cost",
    "weekly_childcare_hours",
    "employer_provided_childcare_cost",
    "has_registered_childcare",
]

CHILDCARE_ENUMS = {}
