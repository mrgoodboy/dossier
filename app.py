from flask import Flask
import hashlib
import dossier
from flask import request,jsonify,redirect,Response
import json

app = Flask(__name__)
print "Starting webapp!"

@app.route('/api/tester', methods = ['POST'])
def echo():
	return request.data

@app.route('/api/photoupload', methods = ['POST'])
def photoupload():
	file = request.files['file']
	sum=md5sum(file)
	if file and allowed_file(sum):
		filename = secure_filename(sum)+'.wav'
		file.save(os.path.join('/audio/', filename))
        return filename
	return False		


if __name__ == '__main__':
    app.run(host='0.0.0.0')

