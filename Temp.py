import os
import shutil
class normTemp:
    def __init__(self,temp_path):
        Temp_2=r"C:\Windows\Temp"
        file_names=os.listdir(Temp_2)
        for file in file_names:    #loops and takes name of all the files in folder one by one
            file_path=os.path.join(Temp_2, file)    #mixes the filename to the directory inorder to target the file
            dest_path=os.path.join(temp_path,file)    #mixes the filename to destination name where it will be moved
            try:
                shutil.move(file_path, temp_path)
            except PermissionError:
                continue    #to skip through files with admin permission
            except WindowsError:
                continue    #to skip through files that are currently in use
            except:
                try:
                    os.remove(dest_path)    #trying to remove the file/folder from repeating in temporary folder
                    shutil.move(file_path,temp_path)
                except:
                    pass
