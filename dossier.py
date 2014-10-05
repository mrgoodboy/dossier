import json
import time
import requests
from alchemyapi import AlchemyAPI
from iodpython.iodindex import IODClient
import os


ALCHEMYAPI_KEY = os.environ("DOSSIER_ALCHEMY_KEY")
ALCHEMY_RELEVANCE_THRESHOLD = 0.7

alchemyapi = AlchemyAPI()
client = IODClient("http://api.idolondemand.com/", os.environ("DOSSIER_IDOL_KEY"))
index = client.getIndex("conversations")
cardIndex = client.getIndex("cards")

'''
original format of transcript is, should be reformatted before

[
{"me":"hello"},
{"you": "hello"}
etc
]

'''

#index a conversation

def dossierConversation(transcript):
	transcript = json.loads(transcript)
	information = extractInformation(transcript)

	preprocessedTranscript = preprocess(transcript)
	concepts = getTopicsFromConversation(preprocessedTranscript)
	segmentedTranscript = generateSegmentedTranscript(transcript, information)

	if "name" in information:
		title = "Conversation with " + information["name"]
		addCardToIndex(information)
	else:
		title = "Conversation"

	print information
	print indexConversation(segmentedTranscript, information["name"], "Conversation with " + information["name"])

def addCardToIndex(information):
	cards = getCard(information["name"])
	doc = { "content": str(information), "title": information["name"], "reference": information["name"] }
	result = cardIndex.addDoc(doc, async=True).json()
	return result


#title should contain persons name
def indexConversation(transcript, person_id, title):
	print "started indexing"
	topics = getTopicsFromConversation(transcript)
	doc = { "content": transcript, "title": title, "reference": str(time.time()), 
	"topics": topics, "date": time.strftime("%m/%d/%y"), "person_id": str(person_id) }
	result = index.addDoc(doc, async=True).json()
	print "finished indexing"
	return result

#queries

def getConversationAbout(topic):
	r = client.post('querytextindex', {'indexes': 'conversations', 'text':topic, 'print': 'all'})
	return r.json()

def getConversationWith(person_id):
	fieldText = 'MATCH{' + person_id + '}:person_id'
	r = client.post('querytextindex', {'indexes': 'conversations', 'text':'*', 'field_text': fieldText, 'print': 'all'})
	return r.json()

def getCards():
	r = client.post('querytextindex', {'indexes': 'cards', 'text':'*', 'print': 'all'})
	return r.json()

def getCard(person_id):
	query = person_id + ":title"
	r = client.post('querytextindex', {'indexes': 'cards', 'text':query, 'print': 'all'})
	return r.json()


### indexer

def generateSegmentedTranscript(transcript, information):
	segmentedTranscript = ""
	meName = "Me: "
	if "name" in information:
		youName = information["name"] + ": "
	else:
		youName = "You: "

	for segment in transcript:
		if segment.keys()[0] == "me":
			segmentedTranscript += meName
		else:
			segmentedTranscript += youName
		segmentedTranscript += segment.values()[0]+"\n"

	return segmentedTranscript

def getTopicsFromConversation(transcript):
	concepts = []
	
	response = alchemyapi.concepts("text", transcript)
	if response['status'] == 'OK':
	    for concept in response['concepts']:
	    	if float(concept['relevance']) > ALCHEMY_RELEVANCE_THRESHOLD:
	    		concepts.append(concept['text'])      
	else:
	    print('Error in concept tagging call: ', response['statusInfo'])
	    return -1

	return concepts


#remove all segmentation
def preprocess(transcript):
	processedTranscript = ""
	for segment in transcript:
		processedTranscript += segment.values()[0]+".\n"
	return processedTranscript

def getEntities(preprocessedTranscript):
	response = alchemyapi.entities('text', preprocessedTranscript)
	entities = response['entities']
	return entities

#returns the text of valid entities
def entityOfTypeInSegment(types, segment, entities):
	validEntities = []
	for entity in entities:
		if entity['type'] in types:
			if entity['text'] not in validEntities:
				validEntities.append(entity['text'])
	return validEntities

def extractInformation(transcript):

	preprocessedTranscript = preprocess(transcript)
	entities = getEntities(preprocessedTranscript)
	information = {}

	#prepare keywords
	response = alchemyapi.keywords('text', preprocessedTranscript, {'sentiment': 1})
	keywords = []
	for kw in response["keywords"]:
		if float(kw["relevance"]) > 0.5:
			keywords.append(kw)

	for segment in transcript:
		if 'you' in segment:
			segment = segment["you"]
			#name
			element = listElementInString(["I'm ", "I am", "My name is ", "my name is ", "people call me ", "People call me "], segment)
			if element:
				people = entityOfTypeInSegment(['Person'], segment, entities)
				firstWord = segment.split(element)[1].split()[0]
				name = entityTextForWord(firstWord, people)
				if name:
					information["name"] = name

			#school
			element = listElementInString(["I go to ", "I study at ", "I attend ", "I went to ",
			 "I studied at ", "I attended ", "I graduated from "], segment)
			if element:
				schools = entityOfTypeInSegment(['Organization'], segment, entities)
				firstWord = segment.split(element)[1].split()[0]
				school = entityTextForWord(firstWord, schools)
				if school:
					information["school"] = school

			#employer
			element = listElementInString(["I work at ", "I work for "], segment)
			if element:
				employers = entityOfTypeInSegment(['Company', 'Organization'], segment, entities)
				firstWord = segment.split(element)[1].split()[0]
				employer = entityTextForWord(firstWord, employers)
				if employer:
					information["employer"] = employer

			#jobtitle
			element = listElementInString(["I work as a", "I work as an ", "I work as, " "I am a ",
			 "I am an ", "I am ", "I'm", "I'm a ", "I'm an "], segment)
			if element:
				jobs = entityOfTypeInSegment(['JobTitle'], segment, entities)
				firstWord = segment.split(element)[1].split()[0]
				job = entityTextForWord(firstWord, jobs)
				if job:
					information["job"] = job

			#hometown/homecountry
			element = listElementInString(["I'm from ", "I am from ", "I live in "], segment)
			if element:
				homes = entityOfTypeInSegment(['City', 'Country', 'StateOrCounty'], segment, entities)
				firstWord = segment.split(element)[1].split()[0]
				home = entityTextForWord(firstWord, homes)
				if home:
					information["home"] = home

			#extract what I like and hate
			keywordsInSegment = findKeywordsInSegment([k["text"] for k in keywords], segment)
			for kwsgm in keywordsInSegment:
				for keyword in keywords:
					if kwsgm == keyword["text"]:
						if keyword["sentiment"]["type"] == "positive":
							if float(keyword["sentiment"]["score"]) < 0.6:
								continue
							if "interests" in information:
								information["interests"].append(kwsgm)
							else:
								information["interests"] = [kwsgm]
						elif keyword["sentiment"]["type"] == "negative":
							if float(keyword["sentiment"]["score"]) > -0.6:
								continue
							if "dislikes" in information:
								information["dislikes"].append(kwsgm)
							else:
								information["dislikes"] = [kwsgm]

	return information


def entityTextForWord(word, entities):
	for entity in entities:
		if word in entity:
			return entity
	return False

def listElementInString(list, string):
	for element in list:
		if element in string:
			return element
	return False

def findKeywordsInSegment(keywords, segment):
	keywordsInSegment = []
	for keyword in keywords:
		if keyword in segment:
			keywordsInSegment.append(keyword)
	return keywordsInSegment




