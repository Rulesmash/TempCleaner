import os
import shutil
class perc_temp:
    def __init__(self):
        mainfile=os.getenv("TEMP")
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
