from percentage_Temp import perc_temp
from Temp import normTemp
class deleter():
    def __init__(self,condition):
        match condition:
            case 1:
                perc_temp()
            case 2:
                normTemp()
            case 3:
                normTemp()
                perc_temp()
