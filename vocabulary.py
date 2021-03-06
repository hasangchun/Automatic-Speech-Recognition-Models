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
import numpy as np
import Levenshtein as Lev
from torch import Tensor
from typing import Tuple, Optional, Any


def load_label(label_path: str, blank_id: int) -> Tuple[dict, dict]:
    """
    Create dictionaries that can convert char to id and id to char

    Args:
        label_path (str): path which id and char are mapped
        blank_id (int): blank number

    Returns: char2id, id2char
        - **char2id** (dict): dictionary that converts char to id
        - **id2char** (dict): dictionary that converts id to char
    """
    char2id = dict()
    id2char = dict()

    file = pd.read_csv(label_path, encoding='utf-8')

    id_list = file['id']
    char_list = file['char']

    for id, char in zip(id_list, char_list):
        char2id[char] = id
        id2char[id] = char

    char2id['<blank>'] = blank_id
    id2char[blank_id] = '<blank>'

    return char2id, id2char


def load_dataset(dataset_path: str, mode: str) -> Tuple[list, list, list, list]:
    """
    Divide all audio paths and transcripts into train and validate

    Args:
        dataset_path (str): path with audio and transcript
        mode (str): flag indication train or eval

    Returns: train_audio_paths, train_transcripts, valid_audio_paths, valid_transcripts
        - **audio_paths** (list): list of audio paths to train or eval
        - **transcripts** (list): list of transcripts to train or eval
        - **valid_audio_paths** (list): list of audio paths to validate, if mode is eval, return None
        - **valid_transcripts** (list): list of transcripts to validate, if mode is eval, return None
    """
    audio_paths = list()
    transcripts = list()

    valid_audio_paths = None
    valid_transcripts = None

    if mode == 'train':  # Dataset with the maximum label length truncated to 100
        TRAIN_NUM = 410000
        VALID_NUM = 5279

        with open(dataset_path) as f:
            for line in f.readlines():
                audio_path, _, transcript = line.split('\t')
                transcript = transcript.replace('\n', '')

                audio_paths.append(audio_path)
                transcripts.append(transcript)

        temp = list(zip(audio_paths, transcripts))
        np.random.shuffle(temp)
        audio_paths, transcripts = zip(*temp)

        train_audio_paths = audio_paths[:TRAIN_NUM]
        train_transcripts = transcripts[:TRAIN_NUM]

        valid_audio_paths = audio_paths[TRAIN_NUM:]
        valid_transcripts = transcripts[TRAIN_NUM:]

        audio_paths = train_audio_paths
        transcripts = train_transcripts

    elif mode == 'eval':
        with open(dataset_path) as f:
            for line in f.readlines():
                audio_path, _, transcript = line.split('\t')
                transcript = transcript.replace('\n', '')

                audio_paths.append(audio_path)
                transcripts.append(transcript)

    return audio_paths, transcripts, valid_audio_paths, valid_transcripts


def label_to_string(
        eos_id: int,
        blank_id: int,
        labels: Tensor,
        id2char: dict,
) -> Optional[Any]:
    """
   Converts label to string (number => Korean)

   Args:
       eos_id (int): index of the end of sentence
       blank_id (int): blank number
       labels (Tensor): label number
       id2char (dict): dictionary that converts id to char

   Returns: sentence
       - **sentence** (str or list): changed the label to Korean
    """
    if len(labels.size()) == 1:
        sentence = str()

        for label in labels:
            if label.item() == eos_id:
                break
            if label.item() == blank_id:
                continue
            sentence += id2char[label.item()]
        return sentence

    elif len(labels.size()) == 2:
        sentences = list()
        for label in labels:
            sentence = str()
            for idx in label:
                if idx.item() == eos_id:
                    break
                if idx.item() == blank_id:
                    continue
                sentence += id2char[idx.item()]

            sentences.append(sentence)
        return sentences


def get_distance(
        targets: Tensor,
        y_hats: Tensor,
) -> Tuple[int, int]:
    """
    Calculate distance and length to find cer

    Args:
        targets (Tensor): ground truth
        y_hats (Tensor): predicted sentences

    Returns: total_distance, total_length, transcripts
        - **total_distance** (int): the sum of the distances during the batch size
        - **total_length** (int): the sum of the lengths during the batch size
    """
    total_distance = 0
    total_length = 0

    for target, y_hat in zip(targets, y_hats):
        target = target.replace(' ', '')
        y_hat = y_hat.replace(' ', '')

        distance = Lev.distance(target, y_hat)
        length = len(target.replace(' ', ''))

        total_distance += distance
        total_length += length

    return total_distance, total_length

