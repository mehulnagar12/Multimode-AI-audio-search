import datasets
from datasets import load_dataset
import os

HF_TOKEN = os.environ["HF_TOKEN"]

print("datasets version:", datasets.__version__)

ds = load_dataset(
    "talkbank/callhome",
    "eng",
    use_auth_token=HF_TOKEN,
    streaming=True
)

print(ds)