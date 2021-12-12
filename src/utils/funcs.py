import os

def ensure_list_size_with_default(l, size: int, default):
    l.extend([default] * size)
    return l[0:2]

def get_save_dirs(loc):
    return [d for d in os.listdir(loc) if "SAVEDATA" in d]

def get_active_slot(saves):
    for slot in range(1, len(saves) + 1):
        slot = f"Slot_{slot}"
        if f"SAVEDATA.{slot}" not in saves:
            return slot
    return None

def get_save_info(save_dir):
    meta = os.path.join(save_dir, "meta.txt")
    if not os.path.exists(meta):
        return "", ""
    
    with open(meta, "r") as f:
        return ensure_list_size_with_default(f.readlines(), 2, "")