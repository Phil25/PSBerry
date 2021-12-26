import os
import socket

def ensure_list_size_with_default(l, size: int, default):
    l.extend([default] * size)
    return l[0:2]

def get_save_dirs(loc):
    if not os.path.exists(loc):
        return []
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

def format_bytes(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"

# https://stackoverflow.com/a/28950776/13156175
def get_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        address = s.getsockname()[0]
    except Exception:
        address = "127.0.0.1"
    finally:
        s.close()
    return address