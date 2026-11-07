import os
import numpy as np
import pandas as pd
import torch
import logging
import pkg_resources
from rxnfp.models import SmilesClassificationModel

logger = logging.getLogger(__name__)

# Path to the trained model directory
train_model_path = "./model/ecreact_model"
model = SmilesClassificationModel("bert", train_model_path, use_cuda=torch.cuda.is_available())

# Load the queries from the text file (one query per row, no header)
queries_df = pd.read_csv("./DB/test.csv")
queries = queries_df["rxn_smiles"].dropna().tolist()


# Predict for the loaded queries
predictions = model.predict(queries)

print("Number of queries:", len(queries))


# Create a DataFrame with reaction IDs and predictions
results_df = pd.DataFrame({
    "Reaction": queries,
    "Prediction": predictions[0]
})

# Print the first few rows of the DataFrame to verify the output
print(results_df.head())
results_df.to_csv("./Results/results_test.csv", index=False)