#    Copyright 2020 Division of Medical Image Computing, German Cancer Research Center (DKFZ), Heidelberg, Germany
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


import argparse
from batchgenerators.utilities.file_and_folder_operations import *
from d_lka_former.run.default_configuration import get_default_configuration
from d_lka_former.paths import default_plans_identifier
from d_lka_former.utilities.task_name_id_conversion import convert_id_to_task_name
import numpy as np
import torch

import importlib

# from d_lka_former.network_architecture.synapse.transformerblock import TransformerBlock, TransformerBlock_3D_LKA, TransformerBlock_LKA_Channel, TransformerBlock_SE, TransformerBlock_Deform_LKA_Channel, TransformerBlock_Deform_LKA_Channel_sequential, TransformerBlock_3D_LKA_3D_conv, TransformerBlock_LKA_Channel_norm, TransformerBlock_LKA_Spatial, TransformerBlock_Deform_LKA_Spatial_sequential, TransformerBlock_Deform_LKA_Spatial, TransformerBlock_3D_single_deform_LKA
# from d_lka_former.network_architecture.acdc.transformerblock import TransformerBlock, TransformerBlock_3D_single_deform_LKA
seed = 42
np.random.seed(seed)
os.environ["PYTHONHASHSEED"] = str(seed)
np.random.seed(seed)
torch.manual_seed(seed)
torch.cuda.manual_seed(seed)
torch.cuda.manual_seed_all(seed)
torch.backends.cudnn.deterministic = False
torch.backends.cudnn.benchmark = True
torch.backends.cudnn.enabled = True


# to improve the efficiency set the last two true


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("network")
    parser.add_argument("network_trainer")
    parser.add_argument("task", help="can be task name or task id")
    parser.add_argument("fold", help="0, 1, ..., 5 or 'all'")
    parser.add_argument(
        "-val",
        "--validation_only",
        help="use this if you want to only run the validation",
        action="store_true",
    )
    parser.add_argument(
        "-c",
        "--continue_training",
        help="use this if you want to continue a training",
        action="store_true",
    )
    parser.add_argument(
        "-p",
        help="plans identifier. Only change this if you created a custom experiment planner",
        default=default_plans_identifier,
        required=False,
    )
    parser.add_argument(
        "--use_compressed_data",
        default=False,
        action="store_true",
        help="If you set use_compressed_data, the training cases will not be decompressed. "
        "Reading compressed data is much more CPU and RAM intensive and should only be used if "
        "you know what you are doing",
        required=False,
    )
    parser.add_argument(
        "--deterministic",
        help="Makes training deterministic, but reduces training speed substantially. I (Fabian) think "
        "this is not necessary. Deterministic training will make you overfit to some random seed. "
        "Don't use that.",
        required=False,
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--npz",
        required=False,
        default=False,
        action="store_true",
        help="if set then model will "
        "export npz files of "
        "predicted segmentations "
        "in the validation as well. "
        "This is needed to run the "
        "ensembling (if needed)",
    )
    parser.add_argument(
        "--find_lr",
        required=False,
        default=False,
        action="store_true",
        help="not used here, just for fun",
    )
    parser.add_argument(
        "--valbest",
        required=False,
        default=False,
        action="store_true",
        help="hands off. This is not intended to be used",
    )
    parser.add_argument(
        "--fp32",
        required=False,
        default=True,
        action="store_true",
        help="disable mixed precision training and run old school fp32",
    )
    parser.add_argument(
        "--val_folder",
        required=False,
        default="validation_raw",
        help="name of the validation folder. No need to use this for most people",
    )
    parser.add_argument(
        "--disable_saving",
        required=False,
        action="store_true",
        help="If set nnU-Net will not save any parameter files (except a temporary checkpoint that "
        "will be removed at the end of the training). Useful for development when you are "
        "only interested in the results and want to save some disk space",
    )
    parser.add_argument(
        "--disable_postprocessing_on_folds",
        required=False,
        action="store_true",
        help="Running postprocessing on each fold only makes sense when developing with nnU-Net and "
        "closely observing the model performance on specific configurations. You do not need it "
        "when applying nnU-Net because the postprocessing for this will be determined only once "
        "Usually running postprocessing on each fold is computationally cheap, but some users have "
        "reported issues with very large images. If your images are large (>600x600x600 voxels) "
        "you should consider setting this flag.",
    )
    parser.add_argument(
        "--val_disable_overwrite",
        action="store_false",
        default=True,
        help="Validation does not overwrite existing segmentations",
    )
    parser.add_argument(
        "--disable_next_stage_pred",
        action="store_true",
        default=False,
        help="do not predict next stage",
    )
    parser.add_argument(
        "-pretrained_weights",
        type=str,
        required=False,
        default=None,
        help="path to nnU-Net checkpoint file to be used as pretrained model (use .model "
        "file, for example model_final_checkpoint.model). Will only be used when actually training. "
        "Optional. Beta. Use with caution.",
    )

    """ LEON HERE"""
    parser.add_argument(
        "--trans_block",
        default="TransformerBlock",
        type=str,
        help="The chosen Transformerblock. There are several different to choose from.",
    )

    parser.add_argument(
        "--depths",
        required=False,
        default=3,
        type=int,
        help="Depth of the Transformerblocks per stage.",
    )

    parser.add_argument(
        "--skip_connections",
        required=False,
        default=4,
        type=int,
        help="Number of skip connections in the network.",
    )
    parser.add_argument(
        "--seed", type=int, default=12345, help="Seed for reproducing the training."
    )
    args = parser.parse_args()

    task = args.task
    fold = args.fold
    network = args.network
    network_trainer = args.network_trainer
    validation_only = args.validation_only
    plans_identifier = args.p
    find_lr = args.find_lr
    disable_postprocessing_on_folds = args.disable_postprocessing_on_folds

    use_compressed_data = args.use_compressed_data
    decompress_data = not use_compressed_data

    deterministic = args.deterministic
    valbest = args.valbest

    fp32 = args.fp32
    run_mixed_precision = not fp32

    val_folder = args.val_folder

    """ Leon Here doing stuff"""
    if args.network_trainer == "d_lka_former_trainer_synapse":
        module = importlib.import_module(
            "d_lka_former.network_architecture.synapse.transformerblock"
        )
    elif args.network_trainer == "d_lka_former_trainer_acdc":
        module = importlib.import_module(
            "d_lka_former.network_architecture.acdc.transformerblock"
        )
    trans_block_class = getattr(module, args.trans_block)
    print("Transblock class: {}".format(trans_block_class))
    depths = [args.depths, args.depths, args.depths, args.depths]
    print("Depths: {}".format(depths))
    if args.skip_connections == 4:
        skip_connections = [True, True, True, True]
        print("Using 4 skip connections.")
    elif args.skip_connections == 3:
        skip_connections = [True, True, True, False]
        print("Using 3 skip connections.")
    elif args.skip_connections == 2:
        skip_connections = [True, True, False, False]
        print("Using 2 skip connections.")
    elif args.skip_connections == 1:
        skip_connections = [True, False, False, False]
        print("Using 1 skip connection.")
    elif args.skip_connections == 0:
        skip_connections = [False, False, False, False]
        print("Using 0 skip connections.")
    else:
        raise RuntimeError(
            "Number of skip connections must be between 0 and 4, but it is: {}".format(
                args.skip_connections
            )
        )

    if not task.startswith("Task"):
        task_id = int(task)
        task = convert_id_to_task_name(task_id)

    if fold == "all":
        pass
    else:
        fold = int(fold)

    (
        plans_file,
        output_folder_name,
        dataset_directory,
        batch_dice,
        stage,
        trainer_class,
    ) = get_default_configuration(network, task, network_trainer, plans_identifier)
    print(f"plans_file: {plans_file}")
    print(f"output_folder_name: {output_folder_name}")
    print(f"dataset_directory: {dataset_directory}")
    print(f"batch_dice: {batch_dice}")
    print(f"stage: {stage}")
    print(f"trainer_class: {trainer_class}")
    if trainer_class is None:
        raise RuntimeError(
            "Could not find trainer class in d_lka_former.training.network_training"
        )

    trainer = trainer_class(
        plans_file,
        fold,
        output_folder=output_folder_name,
        dataset_directory=dataset_directory,
        batch_dice=batch_dice,
        stage=stage,
        unpack_data=decompress_data,
        deterministic=deterministic,
        fp16=run_mixed_precision,
        trans_block=trans_block_class,
        depths=depths,
        skip_connections=skip_connections,
        seed=args.seed,
    )
    if args.disable_saving:
        trainer.save_final_checkpoint = (
            False  # whether or not to save the final checkpoint
        )
        trainer.save_best_checkpoint = (
            False  # whether or not to save the best checkpoint according to
        )
        # self.best_val_eval_criterion_MA
        trainer.save_intermediate_checkpoints = (
            True  # whether or not to save checkpoint_latest. We need that in case
        )
        # the training chashes
        trainer.save_latest_only = (
            True  # if false it will not store/overwrite _latest but separate files each
        )

    trainer.initialize(not validation_only)

    if find_lr:
        trainer.find_lr()
    else:
        if not validation_only:
            if args.continue_training:
                # -c was set, continue a previous training and ignore pretrained weights
                try:
                    trainer.load_latest_checkpoint()
                except:
                    print(
                        "No model found to continue training. Starting from scratch..."
                    )
                    pass
            else:
                # new training without pretraine weights, do nothing
                pass

            trainer.run_training()
        else:
            if valbest:
                trainer.load_best_checkpoint(train=False)
            else:
                trainer.load_final_checkpoint(train=False)

        trainer.network.eval()

        # predict validation
        trainer.validate(
            save_softmax=args.npz,
            validation_folder_name=val_folder,
            run_postprocessing_on_folds=not disable_postprocessing_on_folds,
            overwrite=args.val_disable_overwrite,
        )


if __name__ == "__main__":
    main()
