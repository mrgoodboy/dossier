from flask import Flask
import hashlib
import dossier
from flask import request,jsonify,redirect,Response
from werkzeug import secure_filename
import json
from core import NDEVCredentials
from asr import *
from scipy.io import wavfile
import numpy
import subprocess
import os


app = Flask(__name__)
print "Starting webapp!"


'''
run dossierConversation to add transcript to indexConver
transcript must be segmented and formatted like this

[
{"me":"hello"},
{"you": "hello"}
etc
]

'''


@app.route('/')
def hello_world():
    return getConversations()

@app.route('/', methods = ['POST'])
def upload():
	#somehow extract transcript
	transcript = params['upload']

	card = dossier.dossierConversation(transcript)
	return json.dumps(card['documents'])

@app.route('/api/photoupload', methods = ['POST'])
def photoupload():
	f = request.files['file']
	sum=hashlib.md5(f.read()).hexdigest()
	if f:
		filename = secure_filename(sum)+'.mp4'
		f.seek(0)
		f.save(os.path.join('audio/', filename))
		print "HELLO"
		subprocess.call("faad -o "+os.path.join('audio/', filename[:-4])+".wav "+os.path.join('audio/', filename),shell=True)
		print "GO"
		filename = filename[:-4]+".wav"
		print "WASSUP"
		print("sox "+os.path.join('audio/', filename)+" -c 1 "+os.path.join('audio/', "1"+filename)+" avg -l")
		subprocess.call("sox "+os.path.join('audio/', filename)+" -c 1 "+os.path.join('audio/', "1"+filename),shell=True)
		filename = "1"+filename
		signal = wavfile.read(os.path.join('audio/',filename))
		data = signal[1][1000:] # delete click transient
		print data
		iStrt=data.size
		# threshold to isolate the speech
		tau = 3277# define threshold value from plot
		# search for start of speech value
		for i in range(0,data.size):
		    if data[i] > tau:
		        iStrt = i    # remember first i value that exceeds tau
		        break    # exit loop
		    
		 
		 
		# search for end of speech by applying threshold from the back
		iEnd=0
		for i in range(1,data.size):
		    if data[data.size - i] > tau:
		        iEnd = data.size - i    # remember last i value that exceeds tau
		        break    # exit loop
		    

		speech = data[iStrt - 300:iEnd + 300]# acquire signal before and after thresholds
		 
		speakerA = numpy.zeros(speech.size, dtype=numpy.int16)
		speakerB = numpy.zeros(speech.size,dtype=numpy.int16)
		thresholdPoints = numpy.zeros(speech.size,dtype=numpy.int16)
		counter = 0
		tau2 = 4917
		 
		lastpt = 0
		creds = NDEVCredentials()
		stuffsaid = []
		# Makes vector of 0s and 1s representing the sound file.
		for i in range(4000,speech.size - 4000):
		    if speech[i] > tau:
		        thresholdPoints[(i - 4000):(i + 4000)] = numpy.ones(8000,dtype=numpy.int16)
		for i in range(0,speech.size-1):
		    if thresholdPoints[i] != thresholdPoints[i - 1]:
		        counter = counter + 1
		    	
		    if counter%4 == 1:
		    	lastpt = i
		    if counter%4 == 2:
		    	wavfile.write(os.path.join('audio/',str(i)+filename),8000,speech[lastpt:i])
		        asr_req = ASR.make_request(creds=creds, desired_asr_lang="English (US)", filename=os.path.join('audio/',i+filename))
		        if asr_req.response.was_successful():
					stuffsaid.append(asr_req.response.get_recognition_result())
		        else:
		        	return asr_req.response.error_message
		    if counter%4 == 3:
		    	lastpt = i
		    if counter%4 == 0:
				wavfile.write(os.path.join('audio/',str(i)+filename),8000,speech[lastpt:i])
				asr_req = ASR.make_request(creds=creds, desired_asr_lang="English (US)", filename=os.path.join('audio/',i+filename))
				if asr_req.response.was_successful():
		 			stuffsaid.append(asr_req.response.get_recognition_result())
				else:
					return asr_req.response.error_message
		print stuffsaid
		return processUnstructuredArray(stuffsaid)


	sucks={"response":'no'}
	return jsonify(sucks)		


def processUnstructuredArray(array):
	transcript = []
	for idx, val in enumerate(array):
		if idx % 2 == 0:
			transcript.append({ "me" : val })
		else:
			transcript.append({ "you" : val })

	response = dossier.dossierConversation(transcript)
	print response
	return json.dumps(response['documents'], ensure_ascii=True)

#query methods
@app.route('/api/getcards', methods = ['GET'])
def getCards():
	response = dossier.getCards()
	return json.dumps(response['documents'], ensure_ascii=True)

@app.route('/api/getcard', methods = ['GET', 'POST'])
def getCard():
	response = dossier.getCard(params['person'])
	return json.dumps(response['documents'], ensure_ascii=True)

@app.route('/api/getconversations', methods = ['GET'])
def getConversations():
	response = dossier.getConversations()
	return json.dumps(response['documents'], ensure_ascii=True)

@app.route('/api/getconversationswith', methods = ['GET', 'POST'])
def getConversationsWith():
	response = dossier.getConversationsWith(params['person'])
	return json.dumps(response['documents'], ensure_ascii=True)

@app.route('/api/getconversationsabout', methods = ['GET', 'POST'])
def getConversationsAbout():
	response = dossier.getConversationsAbout(params['topic'])
	return json.dumps(response['documents'], ensure_ascii=True)



if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

