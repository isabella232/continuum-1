'''\
This is a combination of a publisher and subscriber, modeling handling ML workload on the endpoint itself.
'''

import PIL.Image as Image

import tflite_runtime.interpreter as tflite
import numpy as np
import os
import time

CPU_THREADS = int(os.environ['CPU_THREADS'])
FREQUENCY = int(os.environ['FREQUENCY'])

# Set how many imgs to send, and how often
DURATION = 300
SEC_PER_FRAME = float(1 / FREQUENCY)
MAX_IMGS = FREQUENCY * DURATION

# Load the labels
with open('labels.txt', 'r') as f:
    labels = [line.strip() for line in f.readlines()]

# Load the model
interpreter = tflite.Interpreter(
    model_path='model.tflite', num_threads=CPU_THREADS)
interpreter.allocate_tensors()

# Get model input details and resize image
input_details = interpreter.get_input_details()
floating_model = input_details[0]['dtype'] == np.float32

iw = input_details[0]['shape'][2]
ih = input_details[0]['shape'][1]


def main():
    # Loop over the dataset of 60 images
    files = []
    for file in os.listdir('images'):
        if file.endswith('.JPEG'):
            files.append(file)

    print('Start')
    for i in range(MAX_IMGS):
        start_time = time.time_ns()
        image = Image.open('images/' + files[i % len(files)])
        image = image.resize((iw, ih)).convert(mode='RGB')

        input_data = np.expand_dims(image, axis=0)

        if floating_model:
            input_data = (np.float32(input_data) - 127.5) / 127.5

        interpreter.set_tensor(input_details[0]['index'], input_data)

        interpreter.invoke()

        output_details = interpreter.get_output_details()
        output_data = interpreter.get_tensor(output_details[0]['index'])
        results = np.squeeze(output_data)

        top_k = results.argsort()[-5:][::-1]
        for i in top_k:
            if floating_model:
                print( '\t{:08.6f} - {}'.format(float(results[i]), labels[i]))
            else:
                print('\t{:08.6f} - {}'.format(float(results[i] / 255.0), labels[i]))

        # Try to keep a frame rate of X
        sec_frame = time.time_ns() - start_time
        print('Preparation, preprocessing and processing (ns): %i' % (sec_frame))
        sec_frame = float(sec_frame) / 10**9

        if sec_frame < SEC_PER_FRAME:
            # Wait until next frame should happen
            frame = 0.1 * (SEC_PER_FRAME - sec_frame)
            while sec_frame < SEC_PER_FRAME:
                time.sleep(frame)
                sec_frame = float(time.time_ns() - start_time) / 10**9
        else:
            print('Can\'t keep up with %f seconds per frame: Took %f' % (SEC_PER_FRAME, sec_frame))

    print('Finished, processed %i images' % (MAX_IMGS))


if __name__ == '__main__':
    main()
