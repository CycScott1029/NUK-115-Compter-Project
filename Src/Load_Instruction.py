def read_instructions(file_path):
    instructions = []
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            instructions.append(line)
    
    return instructions

def parse_instruction(instruction):
    def parse_operand(operand):
        """Parses individual operands."""
        if '(' in operand and ')' in operand:  # Memory access with offset
            offset, register = operand.split('(')
            register = register.strip(')')
            return {"type": "memory", "register": register, "offset": int(offset)}
        elif operand.startswith('$'):  # Register operand
            return {"type": "register", "register": operand, "offset": None}
        else:  # Immediate value
            return {"type": "immediate", "register": None, "offset": int(operand)}

    # Split instruction and extract components
    parts = instruction.replace(',', '').split()
    operation = parts[0]
    raw_operands = parts[1:]
    
    parsed_operands = [parse_operand(op) for op in raw_operands]

    # Infer rs, rt, rd based on operation type
    if operation in ["add", "sub"]:
        rd = parsed_operands[0]["register"]
        rs = parsed_operands[1]["register"]
        rt = parsed_operands[2]["register"]
        return {
            "operation": operation,
            "rs": rs,
            "rsValue": None,
            "rt": rt,
            "rtValue": None,
            "rd": rd,
            "rdValue": None,
            "offset": None
        }
    elif operation in ["lw", "sw"]:
        rt = parsed_operands[0]["register"]
        rs = parsed_operands[1]["register"]
        offset = parsed_operands[1]["offset"]
        return {
            "operation": operation,
            "rs": rs,
            "rsValue": None,
            "rt": rt,
            "rtValue": None,
            "rd": None,
            "rdValue": None,
            "offset": offset
        }
    elif operation in ["beq"]:
        rs = parsed_operands[0]["register"]
        rt = parsed_operands[1]["register"]
        offset = parsed_operands[2]["offset"]
        return {
            "operation": operation,
            "rs": rs,
            "rt": rt,
            "rd": None,
            "offset": offset
        }


