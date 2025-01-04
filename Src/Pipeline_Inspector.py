class PipelineInspector:
    def __init__(self):
        pass

    def detect_hazard(self, pipeline_register):
        hazards = []

        # Data Hazards: RAW (Read After Write)
        if "ID/EX" in pipeline_register and "EX/MEM" in pipeline_register:
            id_ex_rs = pipeline_register["ID/EX"].get("rs")
            id_ex_rt = pipeline_register["ID/EX"].get("rt")
            ex_mem_rd = pipeline_register["EX/MEM"].get("rd")

            if ex_mem_rd and (id_ex_rs == ex_mem_rd or id_ex_rt == ex_mem_rd):
                hazards.append(("ID/EX", "EX/MEM", "Data Hazard"))

        if "EX/MEM" in pipeline_register and "MEM/WB" in pipeline_register:
            ex_mem_rs = pipeline_register["EX/MEM"].get("rs")
            mem_wb_rd = pipeline_register["MEM/WB"].get("rd")

            if mem_wb_rd and ex_mem_rs == mem_wb_rd:
                hazards.append(("EX/MEM", "MEM/WB", "Data Hazard"))

        # Load-Use Hazard: lw followed by dependent instruction
        if "ID/EX" in pipeline_register and "EX/MEM" in pipeline_register:
            id_ex_rs = pipeline_register["ID/EX"].get("rs")
            id_ex_rt = pipeline_register["ID/EX"].get("rt")
            ex_mem_op = pipeline_register["EX/MEM"].get("op")
            ex_mem_rd = pipeline_register["EX/MEM"].get("rd")

            if ex_mem_op == "lw" and ex_mem_rd and (id_ex_rs == ex_mem_rd or id_ex_rt == ex_mem_rd):
                hazards.append(("ID/EX", "EX/MEM", "Load-Use Hazard"))

        # Control Hazard: beq
        if "IF/ID" in pipeline_register and "ID/EX" in pipeline_register:
            if_id_op = pipeline_register["IF/ID"].get("op")
            id_ex_op = pipeline_register["ID/EX"].get("op")

            if if_id_op == "beq" or id_ex_op == "beq":
                hazards.append(("IF/ID", "ID/EX", "Control Hazard"))

        return hazards

    def analyze_solution(self, hazards):
        solutions = []
        for hazard in hazards:
            stage1, stage2, hazard_type = hazard
            if hazard_type == "Data Hazard" or hazard_type == "Load-Use Hazard":
                solutions.append((hazard, "Forwarding"))
            elif hazard_type == "Control Hazard":
                solutions.append((hazard, "Stalling"))
        return solutions
