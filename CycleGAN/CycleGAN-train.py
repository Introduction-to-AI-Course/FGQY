# -*- coding: utf-8 -*-
"""Untitled0.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1GIR3bv_Da5lmy-lhnNmBGdcLUSFlR-p0
"""

# -*- coding: utf-8 -*-
"""Untitled0.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1cB5TE-yfS6fo_OJNSAv-QhQjIaf8Sf9M
"""

import os
from google.colab import drive
drive.mount('/content/drive')
path = "/content/drive/My Drive"
os.chdir(path)
#!git clone https://github.com/tensorflow/examples.git
from __future__ import absolute_import, division, print_function, unicode_literals
import tensorflow as tf
import tensorflow_datasets as tfds
import sys
sys.path.insert(0, '/content/drive/My Drive/examples/tensorflow_examples/models/pix2pix')
import pix2pix
import os
import time
import matplotlib.pyplot as plt
from IPython.display import clear_output
# 用cpu
# os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
tfds.disable_progress_bar()
AUTOTUNE = tf.data.experimental.AUTOTUNE
PATH = '/content/drive/My Drive/cycleGan/photo2vangogh/'
train_photo = tf.data.Dataset.list_files(PATH + 'trainA/*.jpg')
train_vangogh = tf.data.Dataset.list_files(PATH + 'trainB/*.jpg')
test_photo = tf.data.Dataset.list_files(PATH + 'testA/*.jpg')
test_vangogh = tf.data.Dataset.list_files(PATH + 'testB/*.jpg')
def load(image_file):
    image = tf.io.read_file(image_file)
    image = tf.image.decode_jpeg(image)
    image = tf.cast(image, tf.float32)
    return image
BUFFER_SIZE = 1000
BATCH_SIZE = 1
IMG_WIDTH = 256
IMG_HEIGHT = 256
def random_crop(image):
    cropped_image = tf.image.random_crop(image, size=[IMG_HEIGHT, IMG_WIDTH, 3])
    return cropped_image
# normalizing the images to [-1, 1]
def normalize(image):
    image = tf.cast(image, tf.float32)
    image = (image / 127.5) - 1
    return image
def random_jitter(image):
    # resizing to 286 x 286 x 3
    image = tf.image.resize(image, [286, 286], method=tf.image.ResizeMethod.NEAREST_NEIGHBOR)
    # randomly cropping to 256 x 256 x 3
    image = random_crop(image)
    # random mirroring
    image = tf.image.random_flip_left_right(image)
    return image
def preprocess_image_train(image):
    image = load(image)
    image = random_jitter(image)
    image = normalize(image)
    return image
def preprocess_image_test(image):
    image = load(image)
    image = normalize(image)
    return image
train_photo = train_photo.map(preprocess_image_train, num_parallel_calls=AUTOTUNE).cache().shuffle(BUFFER_SIZE).batch(1)
train_vangogh = train_vangogh.map(preprocess_image_train, num_parallel_calls=AUTOTUNE).cache().shuffle(BUFFER_SIZE).batch(1)
test_photo = test_photo.map(preprocess_image_test, num_parallel_calls=AUTOTUNE).cache().shuffle(BUFFER_SIZE).batch(1)
test_vangogh = test_vangogh.map(preprocess_image_test, num_parallel_calls=AUTOTUNE).cache().shuffle(BUFFER_SIZE).batch(1)

sample_photo = next(iter(train_photo))
sample_vangogh = next(iter(train_vangogh))

plt.subplot(121)
plt.title('Photo')
plt.imshow(sample_photo[0] * 0.5 + 0.5)
plt.subplot(122)
plt.title('Photo with random jitter')
plt.imshow(random_jitter(sample_photo[0]) * 0.5 + 0.5)

plt.subplot(121)
plt.title('Vangogh')
plt.imshow(sample_vangogh[0] * 0.5 + 0.5)
plt.subplot(122)
plt.title('Vangogh with random jitter')
plt.imshow(random_jitter(sample_vangogh[0]) * 0.5 + 0.5)

OUTPUT_CHANNELS = 3
generator_g = pix2pix.unet_generator(OUTPUT_CHANNELS, norm_type='instancenorm')
generator_f = pix2pix.unet_generator(OUTPUT_CHANNELS, norm_type='instancenorm')
discriminator_x = pix2pix.discriminator(norm_type='instancenorm', target=False)
discriminator_y = pix2pix.discriminator(norm_type='instancenorm', target=False)
to_vangogh = generator_g(sample_photo)
to_photo = generator_f(sample_vangogh)
plt.figure(figsize=(8, 8))
contrast = 8
plt.subplot(221)
plt.title('Photo')
plt.imshow(sample_photo[0] * 0.5 + 0.5)
plt.subplot(222)
plt.title('To Vangogh')
plt.imshow(to_vangogh[0] * 0.5 * contrast + 0.5)
plt.subplot(223)
plt.title('Vangogh')
plt.imshow(sample_vangogh[0] * 0.5 + 0.5)
plt.subplot(224)
plt.title('To Photo')
plt.imshow(to_photo[0] * 0.5 * contrast + 0.5)
plt.show()

plt.figure(figsize=(8, 8))
plt.subplot(121)
plt.title('Is a real image by Vangogh?')
plt.imshow(discriminator_y(sample_vangogh)[0, ..., -1], cmap='RdBu_r')
plt.subplot(122)
plt.title('Is a real photo?')
plt.imshow(discriminator_x(sample_photo)[0, ..., -1], cmap='RdBu_r')
plt.show()

LAMBDA = 10
loss_obj = tf.keras.losses.BinaryCrossentropy(from_logits=True)


def discriminator_loss(real, generated):
    real_loss = loss_obj(tf.ones_like(real), real)
    generated_loss = loss_obj(tf.zeros_like(generated), generated)
    total_disc_loss = real_loss + generated_loss
    return total_disc_loss * 0.5


def generator_loss(generated):
    return loss_obj(tf.ones_like(generated), generated)


def calc_cycle_loss(real_image, cycled_image):
    loss1 = tf.reduce_mean(tf.abs(real_image - cycled_image))
    return LAMBDA * loss1


def identity_loss(real_image, same_image):
    loss = tf.reduce_mean(tf.abs(real_image - same_image))
    return LAMBDA * 0.5 * loss


generator_g_optimizer = tf.keras.optimizers.Adam(2e-4, beta_1=0.9)
generator_f_optimizer = tf.keras.optimizers.Adam(2e-4, beta_1=0.9)
discriminator_x_optimizer = tf.keras.optimizers.Adam(2e-4, beta_1=0.9)
discriminator_y_optimizer = tf.keras.optimizers.Adam(2e-4, beta_1=0.9)
checkpoint_path = "./checkpoints1/train"
ckpt = tf.train.Checkpoint(generator_g=generator_g,generator_f=generator_f,
                           discriminator_x=discriminator_x,
                           discriminator_y=discriminator_y,
                           generator_g_optimizer=generator_g_optimizer,
                           generator_f_optimizer=generator_f_optimizer,
                           discriminator_x_optimizer=discriminator_x_optimizer,
                           discriminator_y_optimizer=discriminator_y_optimizer)
ckpt_manager = tf.train.CheckpointManager(ckpt, checkpoint_path, max_to_keep=2)
# if a checkpoint exists, restore the latest checkpoint.
if ckpt_manager.latest_checkpoint:
    ckpt.restore(ckpt_manager.latest_checkpoint)
    print('Latest checkpoint restored!!')
EPOCHS = 40
def generate_images(model, test_input):
    prediction = model(test_input)
    plt.figure(figsize=(12, 12))
    display_list = [test_input[0], prediction[0]]
    title = ['Input Image', 'Predicted Image']
    for i in range(2):
        plt.subplot(1, 2, i + 1)
        plt.title(title[i])
        # getting the pixel values between [0, 1] to plot it.
        plt.imshow(display_list[i] * 0.5 + 0.5)
        plt.axis('off')
    plt.show()

@tf.function
def train_step(real_x,real_y): 
    with tf.GradientTape(persistent=True) as gen_tape, tf.GradientTape(
            persistent=True) as disc_tape:
        fake_y = generator_g(real_x, training=True)
        cycled_x = generator_f(fake_y, training=True)

        fake_x = generator_f(real_y, training=True)
        cycled_y = generator_g(fake_x, training=True)

        same_x = generator_f(real_x, training=True)
        same_y = generator_g(real_y, training=True)

        disc_real_x = discriminator_x(real_x, training=True)
        disc_real_y = discriminator_y(real_y, training=True)
        disc_fake_x = discriminator_x(fake_x, training=True)
        disc_fake_y = discriminator_y(fake_y, training=True)
        # calculate the loss
        gen_g_loss = generator_loss(disc_fake_y)
        gen_f_loss = generator_loss(disc_fake_x)
        total_cycle_loss = calc_cycle_loss(real_x, cycled_x) + calc_cycle_loss(real_y, cycled_y)
        # Total generator loss = adversarial loss + cycle loss
        total_gen_g_loss = gen_g_loss + total_cycle_loss + identity_loss(real_y, same_y)
        total_gen_f_loss = gen_f_loss + total_cycle_loss + identity_loss(real_x, same_x)
        '''total_gen_g_loss = gen_g_loss + calc_cycle_loss(real_x, cycled_x)
    total_gen_f_loss = gen_f_loss + calc_cycle_loss(real_y, cycled_y)'''
        disc_x_loss = discriminator_loss(disc_real_x, disc_fake_x)
        disc_y_loss = discriminator_loss(disc_real_y, disc_fake_y)
    # Calculate the gradients for generator and discriminator
    generator_g_gradients = gen_tape.gradient(total_gen_g_loss, generator_g.trainable_variables)
    generator_f_gradients = gen_tape.gradient(total_gen_f_loss, generator_f.trainable_variables)
    discriminator_x_gradients = disc_tape.gradient(disc_x_loss, discriminator_x.trainable_variables)
    discriminator_y_gradients = disc_tape.gradient(disc_y_loss, discriminator_y.trainable_variables)
    # Apply the gradients to the optimizer
    generator_g_optimizer.apply_gradients(zip(generator_g_gradients, generator_g.trainable_variables))
    generator_f_optimizer.apply_gradients(zip(generator_f_gradients, generator_f.trainable_variables))
    discriminator_x_optimizer.apply_gradients(zip(discriminator_x_gradients, discriminator_x.trainable_variables))
    discriminator_y_optimizer.apply_gradients(zip(discriminator_y_gradients, discriminator_y.trainable_variables))
for epoch in range(EPOCHS):
    start = time.time()
    n = 0
    for image_x, image_y in tf.data.Dataset.zip((train_photo, train_vangogh)):
        train_step(image_x, image_y)
        if n % 10 == 0:
            print('.', end='')
        n += 1
    clear_output(wait=True)
    generate_images(generator_g, sample_photo)
    if (epoch + 1) % 5 == 0:
        ckpt_save_path = ckpt_manager.save()
        print('Saving checkpoint for epoch {} at {}'.format(epoch + 1, ckpt_save_path))
    print('Time taken for epoch {} is {} sec\n'.format(epoch + 1, time.time() - start))
# Run the trained model on the test datasetfor inp in test_vangogh.take(5):  generate_images(generator_g, inp)

for inp in test_photo.take(5):
    generate_images(generator_g, inp)
