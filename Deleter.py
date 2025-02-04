from percentage_Temp import percTemp
from Temp import normTemp
import os
class deleter(): #works by making a folder named Temporary Files and move all the files from temp and %temp% to it (if any file cant be moved due to it being in use, then it produces a copy instead)
    def __init__(self,condition):
        username=os.getlogin()    #to take username and use it to navigate through directories with usernames
        temp_file=f'C:\\Users\\{username}\\Desktop\\Temporary Files'
        if not os.path.exists(temp_file):
            os.mkdir(temp_file)    #creates the temporary folder in desktop which can be deleted after the program is finished
        match condition:
            case 1:
                percTemp(temp_file,username)
            case 2:
                normTemp(temp_file)
            case 3:
                normTemp(temp_file)
                percTemp(temp_file,username)
