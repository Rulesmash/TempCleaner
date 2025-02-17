from percent_temp import perc_temp
from prefetch import prefetc
from local_temp import normTemp
class deleter():
    def __init__(self,condition):
        match condition:
            case 1:
                perc_temp()
            case 2:
                normTemp()
            case 3:
                prefetc()
            case 4:
                normTemp()
                perc_temp()
                prefetc()
