from frs.table_utils import *

def parse_extchild(line, benunit):
    benunit["ext_child_maintenance"] = yearly(line["NHHAMT"], from_period=line["NHHPD"])
    return benunit

EXTCHILD_FILENAMES = ["ext_child_maintenance"]

EXTCHILD_ENUMS = {}