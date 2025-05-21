"""
This modules adds monitoring support of the experiments via Weights and Biases.
"""

from core import BaseNumpyroModel
import wandb

def start_experiment(experiment_name: str, model: BaseNumpyroModel):
    wandb.init(experiment_name)
