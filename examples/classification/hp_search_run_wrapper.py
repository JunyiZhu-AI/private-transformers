"""Wrapper launcher script."""

import os
import math
import fire


def _get_command(
    task_name,
    output_dir,
    model_name_or_path,
    data_dir,
    ghost_clipping,
    non_private,
    target_epsilon,
    few_shot_type,
    freeze_end,
    freeze_rate,
    per_device_train_batch_size=1,
    per_device_eval_batch_size=50,
    eval_steps=10,
    seed=0,
    epoch=6.0,
    clip=0.1,
    momentum=0.9,
    weight_decay=1e-2
):
    # This batch size selection roughly ensures the sampling rates on different
    # datasets are in the same ballpark.
    batch_size = {
        "sst-2": 1000,
        "mnli": 6000,
        "qqp": 6000,
        "qnli": 2000,
    }[task_name]
    gradient_accumulation_steps = batch_size // per_device_train_batch_size

    data_dir_suffix = {
        "sst-2": "GLUE-SST-2",
        "mnli": "MNLI",
        "qqp": "QQP",
        "qnli": "QNLI",
    }[task_name]
    data_dir = f"{data_dir}/{data_dir_suffix}"

    template = {
        "sst-2": "*cls**sent_0*_It_was*mask*.*sep+*",
        "mnli": "*cls**sent-_0*?*mask*,*+sentl_1**sep+*",
        "qnli": "*cls**sent-_0*?*mask*,*+sentl_1**sep+*",
        "qqp": "*cls**sent-_0**mask*,*+sentl_1**sep+*",
    }[task_name]

    # Epochs chosen roughly to match e2e number of updates. We didn't hyperparameter tune on classification tasks :)
    return f'''
python -m classification.run_classification \
  --task_name {task_name} \
  --data_dir {data_dir} \
  --output_dir {output_dir} \
  --overwrite_output_dir \
  --model_name_or_path {model_name_or_path} \
  --few_shot_type {few_shot_type} \
  --num_k 1 \
  --num_sample 1 --seed 0 \
  --template {template} \
  --non_private {non_private} \
  --num_train_epochs {epoch} \
  --target_epsilon {target_epsilon} \
  --per_device_train_batch_size {per_device_train_batch_size} \
  --gradient_accumulation_steps {gradient_accumulation_steps} \
  --per_device_eval_batch_size 8 \
  --per_example_max_grad_norm {clip} --ghost_clipping {ghost_clipping} \
  --learning_rate 0.0005 \
  --lr_decay yes \
  --adam_epsilon 1e-08 \
  --weight_decay 0 \
  --max_seq_len 256 \
  --evaluation_strategy steps --eval_steps {eval_steps} --evaluate_before_training True \
  --do_train --do_eval \
  --first_sent_limit 200 --other_sent_limit 200 --truncate_head yes \
  --freeze_end {freeze_end} \
  --freeze_rate {freeze_rate} \
  --seed {seed} \
  --adam_beta1 {momentum} \
  --per_device_eval_batch_size {per_device_eval_batch_size} \
  --weight_decay {weight_decay}
    '''


def main(
    output_dir,
    task_name,
    process,
    per_device_train_batch_size,
    few_shot_type="prompt",
    model_name_or_path="roberta-base",
    data_dir="classification/data/original",
    ghost_clipping="yes",
    non_private="no",
    target_epsilon=8,
    epoch=6.0,
    momentum=0.9,
    clip=0.1,
):
    rate = [0.3, 0.5, 0.7, 0.9, 0]
    e = [epoch, float(math.ceil(epoch * 1.2))]
    m = [momentum, 0]
    combinations = []
    for r_ in rate:
        for e_ in e:
            for m_ in m:
                combinations.append([r_, e_, m_])
    freeze_rate, epoch, momentum = combinations[process]
    command = _get_command(
        output_dir=output_dir,
        task_name=task_name,
        model_name_or_path=model_name_or_path,
        data_dir=data_dir,
        ghost_clipping=ghost_clipping,
        non_private=non_private,
        target_epsilon=target_epsilon,
        freeze_end=int(epoch),
        freeze_rate=freeze_rate,
        few_shot_type=few_shot_type,
        per_device_train_batch_size=per_device_train_batch_size,
        per_device_eval_batch_size=50,
        seed=0,
        epoch=epoch,
        momentum=momentum,
        clip=clip,
        weight_decay=0,
    )
    print('Running command:')
    print(command)
    os.system(command)


if __name__ == "__main__":
    fire.Fire(main)
