import sys
import os
import pandas as pd
sys.path.insert(0, r"c:\INTER(Genesis)\ai_chatbat_cam_anaylz")
from modules.ai_conversation import generate_conversational_response

df = pd.DataFrame({"Department": ["Sales", "HR"], "Budget": [1000, 500]})
res = generate_conversational_response("What department has the lowest budget?", df, "HR has the lowest budget.")
print("Response length:", len(res))
if len(res) == 0:
    print("Empty response! Rate limit?")
else:
    print("Response:", res[:200])
