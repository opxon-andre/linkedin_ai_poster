import os
import time
import sys

sys.path.append(os.path.join(os.path.dirname(sys.path[0])))

import app.main as dbg



if __name__ == "__main__":
    #dbg.run_scheduler(10)
    #dbg.create_and_save_post()
    dbg.start()
            