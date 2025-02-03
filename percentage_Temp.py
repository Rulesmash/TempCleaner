import os
import shutil
class percTemp:
    def __init__(self,temp_path,username):
        Temp_1=f"C:\\Users\\{username}\\AppData\\Local\\Temp"
        file_names=os.listdir(Temp_1)
        for file in file_names:
            file_path=os.path.join(Temp_1, file)
            dest_path=os.path.join(temp_path,file)
            try:
                shutil.move(file_path, temp_path)
            except PermissionError:
                continue
            except WindowsError:
                continue
            except:
                try:
                    os.remove(dest_path)
                    shutil.move(file_path,temp_path)
                except:
                    pass
