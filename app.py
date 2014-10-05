from flask import Flask
import hashlib
import dossier
from flask import request,jsonify,redirect,Response
import json

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
    return 'Dossier is the shit!'

@app.route('/', methods = ['POST'])
def upload():
	#somehow extract transcript
	transcript = params['upload']

	card = dossier.dossierConversation(transcript)
	return json.dumps(card['documents'])

@app.route('/api/photoupload', methods = ['POST'])
def photoupload():
	file = request.files['file']
	sum=md5sum(file)
	if file and allowed_file(sum):
		filename = secure_filename(sum)+'.wav'
		file.save(os.path.join('/audio/', filename))
        return filename
	return False		




#query methods
@app.route('/api/getcards', methods = ['GET'])
def getCards():
	response = dossier.getCards()
	return json.dumps(response['documents'])

@app.route('/api/getcard', methods = ['GET', 'POST'])
def getCard():
	response = dossier.getCard(params['person'])
	return json.dumps(response['documents'])

@app.route('/api/getconversations', methods = ['GET'])
def getConversations():
	response = dossier.getConversations()
	return json.dumps(response['documents'])

@app.route('/api/getconversationswith', methods = ['GET', 'POST'])
def getConversationsWith():
	response = dossier.getConversationsWith(params['person'])
	return json.dumps(response['documents'])

@app.route('/api/getconversationsabout', methods = ['GET', 'POST'])
def getConversationsAbout():
	response = dossier.getConversationsAbout(params['topic'])
	return json.dumps(response['documents'])



if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

