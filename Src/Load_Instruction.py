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
    parts = instruction.replace(',', '').split()
    operation = parts[0]
    operands = parts[1:]
    
    return {
        "operation": operation,
        "operands": operands
    }

