from MIPS_instruction import MIPS_Instruction

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
    # Remove commas and split the instruction into parts
    parts = instruction.replace(',', '').split()
    operation = parts[0]  # The operation (e.g., 'add', 'lw', etc.)
    operands = parts[1:]  # The operands (e.g., ['$1', '$2', '$3'])

    # Map registers and immediate values
    rs = None
    rt = None
    rd = None
    immediate = None

    if operation in ['add', 'sub']:  # R-type instructions
        rd, rs, rt = operands
    elif operation in ['lw', 'sw']:  # I-type instructions
        rt, offset_base = operands
        offset, rs = offset_base.split('(')
        rs = rs.replace(')', '')
        immediate = int(offset)
    elif operation in ['beq']:  # Branch instruction
        rs, rt, immediate = operands
        immediate = int(immediate)

    # Create a MIPS_Instruction object
    return MIPS_Instruction({
        "operation": operation,
        "rs": rs,
        "rt": rt,
        "rd": rd,
        "immediate": immediate
    })
