import os
import shutil
class recent_l:
    def __init__(self):
        username=os.getlogin()
        mainfile=f"C:\\Users\\{username}\\Recent"
        dst_files=os.listdir(mainfile)
        for file in dst_files:
            rmv_file=os.path.join(mainfile,file)
            if os.path.isfile(rmv_file):
                try:
                    os.remove(rmv_file)
                except:
                    continue
            else:
                try:
                    shutil.rmtree(rmv_file)
                except:
                    continue
