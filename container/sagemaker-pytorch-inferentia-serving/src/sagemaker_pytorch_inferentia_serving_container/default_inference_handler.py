# Copyright 2019-2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from __future__ import absolute_import

import os
import textwrap

import torch
import torch.neuron
from sagemaker_inference import content_types, decoder, default_inference_handler, encoder

class DefaultPytorchInferenceHandler(default_inference_handler.DefaultInferenceHandler):
    VALID_CONTENT_TYPES = (content_types.JSON, content_types.NPY)

    def default_model_fn(self, model_dir):
        """Loads a model. Provides a default implementation.
        Users can provide customized model_fn() in script.
        Args:
            model_dir: a directory where model is saved.
        Returns: A PyTorch model.
        """
        model_files = []
        for f in os.listdir(model_dir):
            if os.path.isfile(f):
                name, ext = os.path.splitext(f)
                if ext == ".pt" or ext == ".pth":
                    model_files.append(f)
        if len(model_files) != 1:
            raise ValueError("Exactly one .pth or .pt file is required for PyTorch models: {}".format(model_files))
        return torch.jit.load(model_files[0])

    def default_input_fn(self, input_data, content_type):
        """A default input_fn that can handle JSON, CSV and NPZ formats.
        Args:
            input_data: the request payload serialized in the content_type format
            content_type: the request content_type
        Returns: input_data deserialized into torch.FloatTensor or torch.cuda.FloatTensor,
            depending if cuda is available.
        """
        np_array = decoder.decode(input_data, content_type)
        tensor = torch.FloatTensor(np_array) if content_type in content_types.UTF8_TYPES else torch.from_numpy(np_array)
        return tensor
        #return torch.tensor(np_array)

    def default_predict_fn(self, data, model):
        """A default predict_fn for PyTorch. Calls a model on data deserialized in input_fn.
        Runs prediction on GPU if cuda is available.
        Args:
            data: input data (torch.Tensor) for prediction deserialized by input_fn
            model: PyTorch model loaded in memory by model_fn
        Returns: a prediction
        """
        return model(data)

    def default_output_fn(self, prediction, accept):
        """A default output_fn for PyTorch. Serializes predictions from predict_fn to JSON, CSV or NPY format.
        Args:
            prediction: a prediction result from predict_fn
            accept: type which the output data needs to be serialized
        Returns: output data serialized
        """
        if type(prediction) == torch.Tensor:
            prediction = prediction.detach().cpu().numpy().tolist()
        encoded_prediction = encoder.encode(prediction, accept)
        if accept == content_types.CSV:
            encoded_prediction = encoded_prediction.encode("utf-8")

        return encoded_prediction
