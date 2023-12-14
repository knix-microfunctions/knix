#   Copyright 2020 The KNIX Authors

#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import tensorflow as tf
 
def handle(event, context):
    # Simple hello world using TensorFlow

    x = [[2.]]
    hello = tf.constant('Hello, TensorFlow!')
    print('tensorflow version', tf.__version__)
    print('hello, {}'.format(tf.matmul(x, x)))

    #return "Hello from Tensorflow " + str(tf.__version__)
    #return "GPU available: " + str(tf.test.is_gpu_available(cuda_only=False, min_cuda_compute_capability=None))
    return "GPU available: " + str(tf.test.is_built_with_cuda())
