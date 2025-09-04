import os
import time
import sys

sys.path.append(os.path.join(os.path.dirname(sys.path[0])))

import main as dbg



if __name__ == "__main__":
    start_time = time.time()
    dbg.main(command="generate")
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.2f} seconds")
            