import os
import shutil

def fix_folders():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "kayan_systemair"))
    target_dir = os.path.join(base_dir, "kayan_systemair")
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    folders_to_move = ["doctype", "page", "report", "workspace", "print_format"]

    for f in folders_to_move:
        src = os.path.join(base_dir, f)
        dst = os.path.join(target_dir, f)
        if os.path.exists(src):
            try:
                shutil.move(src, dst)
                print(f"[\u2713] Moved '{f}' to inner kayan_systemair module directory.")
            except Exception as e:
                print(f"[!] Error moving '{f}': {e}")
        else:
            print(f"[-] Folder '{f}' not found in source or already moved.")

    init_file = os.path.join(target_dir, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as fp:
            fp.write("# init\n")
        print("[\u2713] Created __init__.py in module directory.")

if __name__ == "__main__":
    fix_folders()
