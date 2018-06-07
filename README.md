# Pi-Cam-autoFTP-uploader
A script to automatically take pictures with the raspberry pi's camera and determine if they are different to the last picture that was uploaded to save bandwidth.

I made this script to be used with a pywws weather station on a Raspberry Pi and upload images to wunderground using their FTP service, although this script with probably work with any ftp service that will accept the STOR binary ftp command.

Requires numpy and skimage to be able to process the images.
