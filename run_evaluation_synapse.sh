#!/bin/sh

DATASET_PATH=/cabinet/dataset/Synapse/NN-Unet/DATASET_Synapse
CHECKPOINT_PATH=/cabinet/yousef/synapse/output_synapse_test_lhunet_res_coll_FINETUNE_batch_4_lr_0.007_with_lr_0.00015/
export PYTHONPATH=./
export RESULTS_FOLDER="$CHECKPOINT_PATH"
export d_lka_former_preprocessed="$DATASET_PATH"/d_lka_former_raw/d_lka_former_raw_data/Task02_Synapse
export d_lka_former_raw_data_base="$DATASET_PATH"/d_lka_former_raw

python d_lka_former/run/run_training.py 3d_fullres d_lka_former_trainer_synapse 2 0 -val --trans_block TransformerBlock_3D_single_deform_LKA --depths 3 --skip_connections 4 

