from picamera import *
import picamera
from ftplib import FTP
from PIL import Image
import os
import shutil
import numpy as np
from skimage import color
from skimage import io
from skimage.measure import structural_similarity as ssim
from os import listdir
from os.path import isfile, join
import time
import socket

# Parameters for the FTP server the camera is going to upload to
server = ''  # Server to upload to
username = ''  # Username for server
password = ''  # Password for server

# Folder to archive HD versions of the sent images
archive_folder = '/home/pi/Desktop/Archive/'


class snap:

    def __init__(self):
        self.cam = PiCamera()
        self.cam.resolution = (2844, 1600)
        self.dir = '/home/pi/Desktop/image'  # Working director, 'image' is the beginnings of the filenames
        self.threshold = 1.00  # Value of SSIM (structural similarity)
        self.image_num = 1
        self.image_most_diff = 0
        self.image_last_diff = 0
        self.lastupload_time = time.time()
        self.flag = False  # program is starting
        self.wait_time = 300  # timeout before trying to upload again
        self.uploadthreshold = 0.80  # threshold needed to pass upload to be a 'new' picture
        self.uploads = 0

        self.cleanup()
        self.work()
        
    def cleanup(self):
        onlyfiles = [f for f in listdir('/home/pi/Desktop/') if isfile(join('/home/pi/Desktop/', f))]
        for file in onlyfiles:
            if file[-4:] == ".jpg" and file[5] != "_" \
                    and file[5] != "." or file[-6:] == "HD.jpg":  # Done on reboot to start from fresh number
                os.remove('/home/pi/Desktop/' + file)
        
    def check(self):  # Returns true or false depending on desired image checking
        # resizing the images
        img1 = Image.open('/home/pi/Desktop/image' + str(self.image_num) + '.jpg')
        img2 = Image.open('/home/pi/Desktop/image_sent.jpg')
        img1 = img1.resize((144, 81), Image.ANTIALIAS)
        img2 = img2.resize((144, 81), Image.ANTIALIAS)
        img1.save('/home/pi/Desktop/image_small.jpg')
        img2.save('/home/pi/Desktop/image_sent_small.jpg')

        image1 = io.imread('/home/pi/Desktop/image_small.jpg')
        image2 = io.imread('/home/pi/Desktop/image_sent_small.jpg')
        image1 = color.rgb2gray(image1)
        image2 = color.rgb2gray(image2)
        value = ssim(image1, image2)  # actually checking the value
        print("SSIM value:", value)
        
        if value < self.threshold:
            self.threshold = value
            self.image_last_diff = self.image_most_diff  # recording the iamge so that we can delete it
            self.image_most_diff = self.image_num  # saving the id of the most different image
            return True
        return False

    def work(self):
        print(time.asctime())
        if time.time() - self.lastupload_time > 10000:
            self.uploads = 0  # Resets upload counter if there hasn't been any uploads in over 3 hours
            with open('/home/pi/Desktop/config.txt', 'w') as configfile:
                    configfile.write(str(self.uploads))
        try:
            self.cam.capture(self.dir + str(self.image_num) + '.jpg', resize=(1280, 720))
            self.cam.capture(self.dir + str(self.image_num) + 'HD.jpg')
            new = self.check()
            print("Passes threshold:", new, "Lastdiff", self.image_last_diff,
                  "Mostdiff", self.image_most_diff, "Current", self.image_num)
            if new:
                if self.flag:
                    os.remove(self.dir + str(self.image_last_diff) + '.jpg')  # remove last different picture so we don't have a buildup on new images
                    os.remove(self.dir + str(self.image_last_diff) + 'HD.jpg')
                image = Image.open(self.dir + str(self.image_num) + '.jpg')
                image.save(self.dir + str(self.image_num) + '.jpg', optimize=True, quality=85)  # jpeg compression
                self.flag = True  # because otherwise it crashes trying to delete a non-existent image
            else:
                try:
                    os.remove(self.dir + str(self.image_num) + '.jpg')  # delete current image as it is not different enough
                    os.remove(self.dir + str(self.image_num) + 'HD.jpg')
                except:
                    print("Unable to delete previous pictures, is there write access?")
                    pass
            self.image_num += 1  # increment camera counter

            if time.time() - self.lastupload_time > self.wait_time \
                    and self.threshold < self.uploadthreshold or not self.flag:
                print("uploading")
                ftp = FTP(server)
                ftp.login(username, password)
                with open(self.dir + str(self.image_most_diff) + '.jpg', 'rb') as file:
                    print("FTP Response:", ftp.storbinary('STOR image.jpg', file))
                ftp.close()
                self.threshold = 1.00  # resetting threshold after uploading image
                self.lastupload_time = time.time()
                shutil.copy(self.dir + str(self.image_most_diff) + '.jpg', '/home/pi/Desktop/image_sent.jpg')

                try:
                    file_dir = self.dir + str(self.image_most_diff) + '.jpg'
                    file_mod_time_epoch = os.path.getmtime(file_dir)
                    file_mod_time = time.strftime("%Y-%m-%d %H;%M;%S", time.localtime(file_mod_time_epoch))
                    shutil.copy(self.dir + str(self.image_most_diff) + 'HD.jpg',
                                archive_folder + '{}.jpg'.format(file_mod_time))
                except FileNotFoundError:
                    print("Archive file is not reachable")
                self.uploads += 1
                with open('/home/pi/Desktop/config.txt', 'w') as configfile:
                    configfile.write(str(self.uploads))
            else:
                print("Not uploading")
        except EOFError:
            print("Server terminated connection")

        except PiCameraRuntimeError:
            print("Camera failed to finish capture")
        except socket.gaierror:
            print("No internet connection")
        finally:
            print("=" * 85)


cam = snap()
while True:
    time.sleep(5)
    cam.work()
    time.sleep(10)
    

