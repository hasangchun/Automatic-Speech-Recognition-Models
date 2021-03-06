# MIT License
#
# Copyright (c) 2021 Sangchun Ha
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from typing import Tuple
from vocabulary import get_distance, label_to_string
from data.data_loader import BucketingSampler, AudioDataLoader
from omegaconf import DictConfig


def validate(
        config: DictConfig,
        model: nn.Module,
        device: torch.device,
        valid_loader: AudioDataLoader,
        id2char: dict,
        ctcloss: nn.Module,
        crossentropyloss: nn.Module,
) -> dict:
    validation_epoch_loss = list()
    validation_epoch_cer = list()
    validation_epoch_result = {'validation_loss': validation_epoch_loss, 'validation_cer': validation_epoch_cer}

    total_loss = 0
    total_feature_length = 0
    total_distance = 0
    total_length = 0

    model.eval()

    with torch.no_grad():
        for batch_idx, data in enumerate(valid_loader):
            feature, target, feature_lengths, target_lengths = data

            feature = feature.to(device)
            target = target.to(device)
            feature_lengths = feature_lengths.to(device)
            target_lengths = target_lengths.to(device)

            result = target[:, 1:]

            if config.model.architecture == 'las':
                encoder_output_prob, encoder_output_lengths, decoder_output_prob = model(feature, feature_lengths, None, 0.0)

                decoder_output_prob = decoder_output_prob.to(device)
                decoder_output_prob = decoder_output_prob[:, :result.size(1), :]
                y_hat = decoder_output_prob.max(2)[1]

                if config.model.use_joint_ctc_attention:
                    encoder_output_prob = encoder_output_prob.transpose(0, 1)
                    ctc_loss = ctcloss(encoder_output_prob, target, encoder_output_lengths, target_lengths)

                    cross_entropy_loss = crossentropyloss(
                        decoder_output_prob.contiguous().view(-1, decoder_output_prob.size(2)),
                        result.contiguous().view(-1)
                    )
                    loss = config.model.ctc_weight * ctc_loss + config.model.cross_entropy_weight * cross_entropy_loss

                else:
                    loss = crossentropyloss(
                        decoder_output_prob.contiguous().view(-1, decoder_output_prob.size(2)),
                        result.contiguous().view(-1)
                    )

            elif config.model.architecture == 'deepspeech2':
                output_prob, output_lengths = model(feature, feature_lengths)
                loss = ctcloss(output_prob.transpose(0, 1), target, output_lengths, target_lengths)
                y_hat = output_prob.max(2)[1]

            result = label_to_string(config.train.eos_id, config.train.blank_id, result, id2char)
            y_hat = label_to_string(config.train.eos_id, config.train.blank_id, y_hat, id2char)

            distance, length = get_distance(result, y_hat)

            total_distance += distance
            total_length += length

            total_loss += loss.item()
            total_feature_length += sum(feature_lengths).item()

            average_loss = total_loss / total_feature_length
            average_cer = total_distance / total_length

            if batch_idx % config.train.validation_save_epoch_interval == 0:
                validation_epoch_loss.append(average_loss)
                validation_epoch_cer.append(average_cer)

                print('Loss : {loss:.4f}\t'
                      'Cer : {cer:.2f}\t'.format(loss=average_loss, cer=average_cer))

    return validation_epoch_result


def train(
        config: DictConfig,
        model: nn.Module,
        device: torch.device,
        train_loader: AudioDataLoader,
        valid_loader: AudioDataLoader,
        train_sampler: BucketingSampler,
        optimizer: optim,
        epoch: int,
        id2char: dict,
        epoch_idx: int,
) -> None:
    train_epoch_loss = list()
    train_epoch_cer = list()
    train_epoch_result = {'train_loss': train_epoch_loss, 'train_cer': train_epoch_cer}

    total_distance = 0
    total_length = 0
    ctcloss = nn.CTCLoss(blank=config.train.blank_id, reduction='mean', zero_infinity=True)
    crossentropyloss = nn.CrossEntropyLoss(ignore_index=config.train.pad_id, reduction='mean')

    model.train()

    for batch_idx, data in enumerate(train_loader):
        feature, target, feature_lengths, target_lengths = data

        feature = feature.to(device)
        target = target.to(device)
        feature_lengths = feature_lengths.to(device)
        target_lengths = target_lengths.to(device)

        result = target[:, 1:]

        optimizer.zero_grad()

        if config.model.architecture == 'las':
            encoder_output_prob, encoder_output_lengths, decoder_output_prob = model(feature,
                                                                                     feature_lengths,
                                                                                     target,
                                                                                     config.model.teacher_forcing_ratio)

            decoder_output_prob = decoder_output_prob.to(device)
            decoder_output_prob = decoder_output_prob[:, :result.size(1), :]
            y_hat = decoder_output_prob.max(2)[1]  # (B, T)

            if config.model.use_joint_ctc_attention:
                encoder_output_prob = encoder_output_prob.transpose(0, 1)
                ctc_loss = ctcloss(encoder_output_prob, target, encoder_output_lengths, target_lengths)

                cross_entropy_loss = crossentropyloss(
                    decoder_output_prob.contiguous().view(-1, decoder_output_prob.size(2)),
                    result.contiguous().view(-1)
                )
                loss = config.model.ctc_weight * ctc_loss + config.model.cross_entropy_weight * cross_entropy_loss

            else:
                loss = crossentropyloss(
                    decoder_output_prob.contiguous().view(-1, decoder_output_prob.size(2)),
                    result.contiguous().view(-1)
                )

        elif config.model.architecture == 'deepspeech2':
            output_prob, output_lengths = model(feature, feature_lengths)
            loss = ctcloss(output_prob.transpose(0, 1), target, output_lengths, target_lengths)
            y_hat = output_prob.max(2)[1]

        loss.backward()
        optimizer.step()

        torch.cuda.empty_cache()

        result = label_to_string(config.train.eos_id, config.train.blank_id, result, id2char)
        y_hat = label_to_string(config.train.eos_id, config.train.blank_id, y_hat, id2char)

        distance, length = get_distance(result, y_hat)

        total_distance += distance
        total_length += length

        cer = total_distance / total_length

        if batch_idx % config.train.train_save_epoch_interval == 0:
            train_epoch_loss.append(loss)
            train_epoch_cer.append(cer)

        if config.model.architecture == 'las' and config.model.use_joint_ctc_attention:
            if batch_idx % config.train.print_interval == 0:
                print('Epoch {epoch} : {batch_idx} / {total_idx}\t'
                      'CTC loss : {ctc_loss:.4f}\t'
                      'Cross entropy loss : {cross_entropy_loss:.4f}\t'
                      'loss : {loss:.4f}\t'
                      'cer : {cer:.2f}\t'.format(epoch=epoch, batch_idx=batch_idx, total_idx=len(train_sampler),
                                                 ctc_loss=ctc_loss, cross_entropy_loss=cross_entropy_loss,
                                                 loss=loss, cer=cer))

        else:
            if batch_idx % config.train.print_interval == 0:
                print('Epoch {epoch} : {batch_idx} / {total_idx}\t'
                      'loss : {loss:.4f}\t'
                      'cer : {cer:.2f}\t'.format(epoch=epoch, batch_idx=batch_idx, total_idx=len(train_sampler),
                                                 loss=loss, cer=cer))

    validation_epoch_result = validate(config, model, device, valid_loader, id2char, ctcloss, crossentropyloss)

    save_train_epoch_result(train_epoch_result, config, epoch_idx)
    save_validation_epoch_result(validation_epoch_result, config, epoch_idx)


def save_train_epoch_result(train_epoch_result: dict, config: DictConfig, idx: int):
    result = pd.DataFrame(train_epoch_result)
    result.to_csv(config.train.train_result_path + str(idx) + '.csv', index=False, encoding='cp949')


def save_validation_epoch_result(validation_epoch_result: dict, config: DictConfig, idx: int):
    result = pd.DataFrame(validation_epoch_result)
    result.to_csv(config.train.validation_result_path + str(idx) + '.csv', index=False, encoding='cp949')
