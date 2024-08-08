#------------------------------------------------------------------------------------------------
#                                        IMPORTS
#------------------------------------------------------------------------------------------------
import os
print(f"currently in {os.getcwd()}")
import time
from datetime import datetime

import torch
# Limit PyTorch CUDA use
#torch.cuda.set_per_process_memory_fraction(0.6)
import json

from pathlib import Path

import numpy as np
import wandb

import matplotlib.pyplot as plt
from tabpfn.scripts.model_builder import get_model, save_model
from tabpfn.scripts.model_builder_mamba import get_model_mamba 
from tabpfn.scripts.model_configs import *
from tabpfn.scripts.epoch_callback import epoch_callback

from tabpfn.priors.utils import plot_features
from tabpfn.priors.utils import uniform_int_sampler_f

from evaluation_helper import EvalHelper

#------------------------------------------------------------------------------------------------
#                                       END IMPORTS
#------------------------------------------------------------------------------------------------

#------------------------------------------------------------------------------------------------
#                                        PARAMETER
#------------------------------------------------------------------------------------------------

# Mandatory Parameter
device = "cuda" if torch.cuda.is_available() else "cpu"

# Other Parameters
maximum_runtime = 10000
base_path = '.'
max_features = 100
large_datasets = True
max_samples = 10000 if large_datasets else 5000
bptt = 10000 if large_datasets else 3000
suite='cc'

# Others
json_file_path = "tabpfn_original_config.json"

#------------------------------------------------------------------------------------------------
#                                      END PARAMETER
#------------------------------------------------------------------------------------------------

#------------------------------------------------------------------------------------------------
#                                         CONFIG
#------------------------------------------------------------------------------------------------

with open(json_file_path, "r") as f:
    config = json.load(f)
    
# Fill in stuff that could not be loaded properly into the config.json
uniform_int_sampler_f = (lambda a, b : lambda : round(np.random.uniform(a, b)))
choice_values = [
    torch.nn.modules.activation.Tanh, 
    torch.nn.modules.linear.Identity,
    torch.nn.modules.activation.ReLU
    ]

config["differentiable_hyperparameters"]["prior_mlp_activations"]["choice_values"] = choice_values
config["num_classes"] = uniform_int_sampler_f(2, config['max_num_classes']) # Wrong Function
config["num_features_used"] = uniform_int_sampler_f(1, max_features)

config['batch_size'] = 64 # just because we did this in the other config. Would be 64 default
config['emsize'] = 64 # Default was on 512, just to save some GPU mem.
config["epochs"] = 35
config["bptt"] = 40

config["num_steps"] = 4

config["mamba_num_layers"] = 8
config["mamba_autocast"] = True
config["permutation_repeat"] = 0

device = "cuda:0"
ENABLE_DATA_PARALLEL = False

#os.environ["SLURM_PROCID"]="1"

#------------------------------------------------------------------------------------------------
#                                         END CONFIG
#------------------------------------------------------------------------------------------------

#------------------------------------------------------------------------------------------------
#                                           WANDB
#------------------------------------------------------------------------------------------------

wandb_project = "mamba_project"
wandb_job_type = "create_mamba_model"
wandb_run_name = f"Mamba Large {config['mamba_num_layers']}l {config['emsize']}e {config['batch_size']}b"

wandb_config= config

wandb_run = wandb.init(project=wandb_project,job_type=wandb_job_type,config=wandb_config, name=wandb_run_name, group="DDP")

#------------------------------------------------------------------------------------------------
#                                         END WANDB
#------------------------------------------------------------------------------------------------

#------------------------------------------------------------------------------------------------
#                                           MODEL
#------------------------------------------------------------------------------------------------

# Evaluation during training:
eval_class = EvalHelper()

# Epoch Callback

# Get the model 
#model = get_model(config, device, should_train=True, verbose=0) # , state_dict=model[2].state_dict()
mamba_model = get_model_mamba(config, 
                              device, 
                              should_train=True, 
                              verbose=1,
                              epoch_callback=epoch_callback,
                              mamba_autocast=config["mamba_autocast"], 
                              evaluation_class=eval_class,
                              permutation_repeat=config["permutation_repeat"],
                              enable_data_parallel=ENABLE_DATA_PARALLEL
                              ) # , state_dict=model[2].state_dict()

(hp_embedding, data, _), targets, single_eval_pos = next(iter(mamba_model[3]))

# Save Mamba Model
save_model(mamba_model[2], 
           base_path, 
           f'tabpfn/models_diff/test.cpkt',
           config
           )

#------------------------------------------------------------------------------------------------
#                                         END MODEL
#------------------------------------------------------------------------------------------------


wandb_run.finish()

print("works")
