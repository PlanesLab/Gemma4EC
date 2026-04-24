# BEC-Pred 

Code to train and evaluate [BEC-Pred](https://pubmed.ncbi.nlm.nih.gov/38556873/). Training and evaluation scripts were downloaded and adapted from https://github.com/KeeliaQWJ/BEC-Pred. 

## Requirements

- 1 CUDA-enabled GPU
- 128 GB RAM (required for training and evaluation)
- Conda installed

## Create the Conda Environment

From the project root:

```bash
conda env create -f ./src/bec-pred/becpred_gpu.yml
conda activate becpred_gpu
```

## Run the Pipeline

Make the runner executable:

```bash
chmod +x ./src/bec-pred/run_becpred.sh
```

Run the script:

```bash
bash ./src/bec-pred/run_becpred.sh
```

## What the Script Does

The pipeline automatically runs:

- Database generation from train/test/val CSVs
- Model pretraining with **USPTO** database
- Model finetuning with **train** and **val** datasets
- Model evaluation on **test** dataset
- EC label assignment

## Output

Results are saved in:

```
./src/bec-pred/Results/
```
