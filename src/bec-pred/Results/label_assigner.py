import pandas as pd
import pickle
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--input_csv", type=str, required=True, help="Path to csv with labeled results")
parser.add_argument("--labels", type=str, required=True, help="Path to csv with labels")
parser.add_argument("--output_csv", type=str, required=True, help="Path to output CSV file")
args = parser.parse_args()

labels_path = args.labels
with open(labels_path, 'rb') as f:
    labels_dict = pickle.load(f)

csv_path = args.input_csv
df_predictions = pd.read_csv(csv_path)

df_predictions['Prediction'] = df_predictions['Prediction'].map(labels_dict)

df_predictions.to_csv(args.output_csv, index=False)

print("CSV file has been updated and saved successfully.")
