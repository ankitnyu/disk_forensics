
#! /usr/bin/python
'''	
	Purpose: Get metadat of image and odf file extracted from given disk image.
	Author: Ankit Bang
	Script tested succesfully on Ubuntu 14.04.1
	Script using functions like get_metadata() ,carve(), report_pdf()
	inspired from samples provided.
	
	External references:
		Github
		Cyfor
 
	Script uses haslib for generating md5, sqlite3 to generate database, pyPdf for pdfs
	Python Imaging library PIL, EXIF.
	
	Usage Examples:
	python extractor.py image1,image2
	pyton extractor.py img.txt

	Script store all data sqlite3 database named fingerprint.db
	Data stored in sqlite database is fetched and stored in report.txt	
'''
import os
import re
import sys
import logging
import argparse
import subprocess
import pyPdf
import hashlib
import string
import sqlite3
from PIL import Image
from PIL.ExifTags import TAGS

try:
    from sqlalchemy import Column, Integer, Float, String, Text

    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import create_engine
except ImportError as e:
    print "Module `{0}` not installed".format(error.message[16:])
    sys.exit()

# === SQLAlchemy Config ============================================================================
Base = declarative_base()

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

# === Database Classes =============================================================================
class imageInfo(Base):

    __tablename__ = 'img'

    id = Column(Integer,primary_key = True)
    ImageName = Column(String)
    Label = Column(String)
    Value = Column(String)

    def __init__(self,ImageName,Label,Value,**kwargs):
        self.ImageName=ImageName
        self.Label=Label
        self.Value=Value

# === Fingerprint Classes =========================================================================
class get_metadata(object):
    def __init__(self, img = ''):
        if img == '' or not os.path.exists(img):
            raise Exception('No disk image provided')
           
        self.img = img
        self.fn  = os.path.splitext(os.path.basename(img))[0]
        self.dir = '{0}/extract/{1}'.format(os.path.dirname(os.path.abspath(__file__)), self.fn)
        if not os.path.exists(self.dir): os.makedirs(self.dir)

        self.db = 'fingerprint.db'
        self.engine = create_engine('sqlite:///'+self.db, echo=False)
        Base.metadata.create_all(self.engine)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def carve(self):
        try:
            subprocess.check_output(["tsk_recover","-e",self.img,self.dir])
            subprocess.check_output(["tsk_loaddb","-d","{0}/{1}.db".format(self.dir, self.fn),self.img])
        except:
            raise Exception('Error carving image.')

    def report_pdf(self,filename,item,dat):
	self.filename=filename
	row = imageInfo(filter(lambda x: x in string.printable, filename.decode("utf-8")),str(item), str(dat))
	self.session.add(row)
	self.session.commit()

    def report_exif(self,exif,filename):
	self.exif=exif
	for exifkey,exifval in exif.iteritems():
		self.filename=filename
		row = imageInfo(filter(lambda x: x in string.printable, filename.decode("utf-8")),str(exifkey), str(exifval))
		self.session.add(row)
		self.session.commit()

def report_file():
	DATABASE = sqlite3.connect('fingerprint.db')

	cur = DATABASE.cursor()

	dat = cur.execute("SELECT * FROM img").fetchall()
	fd = open("report.txt", 'w+')
	fd.seek(0)
	for row in dat:
		print row
		fd.write(str(row)+"\n")

	fd.close()	
	DATABASE.close()

def main(argv):
    parser = argparse.ArgumentParser(description='OS Fingerprinting and Carving')
    parser.add_argument('img',help='Disk Image(s) to be analyzed; newline delimited text file or single filename')
    args=parser.parse_args()

    try:
        if os.path.isfile(args.img) and os.path.splitext(os.path.basename(args.img))[1] == '.txt':
            with open(args.img) as ifile:
                imgs = ifile.read().splitlines()
        else:
            raise Exception('')
    except:
        try:
            imgs = [img for img in args.img.split(',')]
        except:
            imgs = args.img

    for img in imgs:
	#print "Hello"
        osf = get_metadata(img)
        osf.carve()
   
    for dirname, dirnames, filenames in os.walk('./extract'):
        for fn in filenames:
            filename = fn
            if (fn.lower()).endswith('pdf'):
                md5 = hashlib.md5(fn).hexdigest()
                #print md5
                try:
                    pdf = pyPdf.PdfFileReader(file(os.path.join(dirname, fn), 'rb'))
                    info = pdf.getDocumentInfo()
                    #print '[*] PDF Metadata: {0}'.format(fn)
                    for item, dat in info.items():
                        try:
                            print '[+] {0}: {1}'.format(item, pdf.resolvedObjects[0][1][item])
			    osf.report_pdf(filename,item,str(format(item, pdf.resolvedObjects[0][1][item])))                   
                        except:
                            print '[+] {0}: {1}'.format(item, dat)
			    osf.report_pdf(filename,item,str(dat))
                except:
                    print "Could not analyze PDF"
		osf.report_pdf(filename,'MD5',md5)

            elif (fn.lower()).endswith('.jpg' or '.jpeg' or '.png' or '.tif' or '.gif' or '.bmp'):
                md5 = hashlib.md5(fn).hexdigest()
                exif = {}
                #print md5
                try:
                    img = Image.open(os.path.join(dirname, fn))
                    info = img._getexif()
                    for tag, value in info.items():
                        decoded = TAGS.get(tag, tag)
                        print "[+] " + decoded + ":", value
                        exif[decoded] = value
                except Exception, e:
                    exif = exif
                    print "Could not retrieve exif data"
		exif['MD5']=md5
		osf.report_exif(exif,filename)

    report_file()
    print 'All images analyzed. Extracted files saved in `./extract/`. Image information saved in `fingerprint.db`'

if __name__ == '__main__':
    main(sys.argv)
