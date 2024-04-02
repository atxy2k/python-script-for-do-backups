import boto3
from config import Config
import os
import time
import zipfile

config_path = os.path.dirname( os.path.realpath(__file__) ) + os.path.sep + 'config.cfg'
config_file = file(config_path)
config = Config(config_file)


filestamp = time.strftime('%Y-%m-%d-%H.%M')

directory = os.path.dirname( os.path.realpath(__file__) ) + os.path.sep + 'backup'

if not os.path.exists(directory):
    os.makedirs(directory)

for the_file in os.listdir(directory):
    file_path = os.path.join(directory, the_file)
    try:
        if os.path.isfile(file_path):
            os.unlink(file_path)
    except Exception as e:
        print(e)


databases = config.databases

for database in databases:
    os.popen("mysqldump -u %s -p%s -h %s --port %s -e --opt -c %s > backup/%s.sql" % (database.user, database.password, database.host, database.port, database.database, database.database + "_" + filestamp))

def zipfolder(foldername, target_dir):
    if( not foldername.endswith('.zip') ):
        foldername = foldername + '.zip'
    zipobj = zipfile.ZipFile(foldername, 'w', zipfile.ZIP_DEFLATED, allowZip64=True)
    rootlen = len(target_dir) + 1
    for base, dirs, files in os.walk(target_dir):
        for file in files:
            fn = os.path.join(base, file)
            zipobj.write(fn, fn[rootlen:])

for directory_object in config.extra_directories:
    if os.path.exists(directory_object.path):
        zipfolder( 'backup'+ os.path.sep + directory_object.name, directory_object.path )
    else:
        print("Directory %s does not exists" % ( directory_object.path ))

filename = 'backup_%s.zip' % (filestamp)

zipfolder( filename, directory )

##Upload

s3 = boto3.client('s3', aws_access_key_id = config.amazon.access_key, aws_secret_access_key = config.amazon.secret_access)
s3_current_bucket = config.amazon.bucket

filepath = os.path.dirname( os.path.realpath(__file__) ) + os.path.sep + filename
s3.upload_file(filename, s3_current_bucket, filename)

try:
    os.remove( filename )
except OSError:
    pass
