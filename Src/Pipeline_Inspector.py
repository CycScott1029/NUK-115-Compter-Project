class PipelineInspector:
    def __init__(self):
        pass

    def detect_hazard(self, pipeline_register):
        hazards = []

        # Data Hazards: RAW (Read After Write)
        if pipeline_register.get("ID/EX") and pipeline_register.get("EX/MEM"):
            id_ex = pipeline_register["ID/EX"]
            ex_mem = pipeline_register["EX/MEM"]

            id_ex_rs = id_ex.get("rs")
            id_ex_rt = id_ex.get("rt")
            ex_mem_rd = ex_mem.get("rd")

            if ex_mem_rd and (id_ex_rs == ex_mem_rd or id_ex_rt == ex_mem_rd):
                hazards.append(("ID/EX", "EX/MEM", "Data Hazard"))

        if pipeline_register.get("EX/MEM") and pipeline_register.get("MEM/WB"):
            ex_mem = pipeline_register["EX/MEM"]
            mem_wb = pipeline_register["MEM/WB"]

            ex_mem_rs = ex_mem.get("rs")
            mem_wb_rd = mem_wb.get("rd")

            if mem_wb_rd and ex_mem_rs == mem_wb_rd:
                hazards.append(("EX/MEM", "MEM/WB", "Data Hazard"))

        # Load-Use Hazard: lw followed by dependent instruction
        if pipeline_register.get("ID/EX") and pipeline_register.get("EX/MEM"):
            id_ex = pipeline_register["ID/EX"]
            ex_mem = pipeline_register["EX/MEM"]

            id_ex_rs = id_ex.get("rs")
            id_ex_rt = id_ex.get("rt")
            ex_mem_op = ex_mem.get("op")
            ex_mem_rd = ex_mem.get("rd")

            if ex_mem_op == "lw" and ex_mem_rd and (id_ex_rs == ex_mem_rd or id_ex_rt == ex_mem_rd):
                hazards.append(("ID/EX", "EX/MEM", "Load-Use Hazard"))

        # Control Hazard: beq
        if pipeline_register.get("IF/ID") and pipeline_register.get("ID/EX"):
            if_id = pipeline_register["IF/ID"]
            id_ex = pipeline_register["ID/EX"]

            if_id_op = if_id.get("op")
            id_ex_op = id_ex.get("op")

            if if_id_op == "beq" or id_ex_op == "beq":
                hazards.append(("IF/ID", "ID/EX", "Control Hazard"))

        return hazards
