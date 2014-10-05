import json
import time
import requests
import collections
from alchemyapi import AlchemyAPI
from iodpython.iodindex import IODClient
import os
import sys


reload(sys)
sys.setdefaultencoding('utf-8')


ALCHEMYAPI_KEY = os.environ["DOSSIER_ALCHEMY_KEY"]
ALCHEMY_RELEVANCE_THRESHOLD = 0.7

alchemyapi = AlchemyAPI()
client = IODClient("http://api.idolondemand.com/", os.environ["DOSSIER_IDOL_KEY"])
index = client.getIndex("conversations")
cardIndex = client.getIndex("cards")



#index a conversation

def dossierConversation(transcript):
	transcript = json.loads(transcript)
	information = extractInformation(transcript)

	if "name" in information:
		title = "Conversation with " + information["name"]
		addCardToIndex(information)
	else:
		information["name"] = ""
		title = "Conversation"

	preprocessedTranscript = preprocess(transcript)
	concepts = getTopicsFromConversation(preprocessedTranscript)
	segmentedTranscript = generateSegmentedTranscript(transcript, information)

	indexConversation(segmentedTranscript, information["name"], "Conversation with " + information["name"])
	return information

def addCardToIndex(information):
	cards = getCard(information["name"])
	doc = { "content": str(information), "title": information["name"], "reference": information["name"] }
	result = cardIndex.addDoc(doc, async=True).json()
	return result


#title should contain persons name
def indexConversation(transcript, person_id, title):
	topics = getTopicsFromConversation(transcript)
	doc = { "content": transcript, "title": title, "reference": str(time.time()), 
	"topics": topics, "date": time.strftime("%m/%d/%y"), "person_id": str(person_id) }
	print doc
	result = index.addDoc(doc, async=True).json()
	return result

#queries

#all conversations
def getConversations():
	r = client.post('querytextindex', {'indexes': 'conversations', 'text':"*", 'print': 'all'})
	return r.json()

def getConversationAbout(topic):
	r = client.post('querytextindex', {'indexes': 'conversations', 'text':topic, 'print': 'all'})
	return r.json()

def getConversationWith(person_id):
	fieldText = 'MATCH{' + person_id + '}:person_id'
	r = client.post('querytextindex', {'indexes': 'conversations', 'text':'*', 'field_text': fieldText, 'print': 'all'})
	return r.json()

#all cards
def getCards():
	r = client.post('querytextindex', {'indexes': 'cards', 'text':'*', 'print': 'all'})
	return r.json()

#card of person_id
def getCard(person_id):
	query = person_id + ":title"
	r = client.post('querytextindex', {'indexes': 'cards', 'text':query, 'print': 'all'})
	return r.json()




### indexer

def generateSegmentedTranscript(transcript, information):
	segmentedTranscript = ""
	meName = "Me: "
	if information["name"]:
		youName = information["name"] + ": "
	else:
		youName = "You: "

	for segment in transcript:
		if segment.keys()[0] == "me":
			segmentedTranscript += meName
		else:
			segmentedTranscript += youName
		segmentedTranscript += segment.values()[0]+"\n"

	return convert(segmentedTranscript)

def getTopicsFromConversation(transcript):
	concepts = []
	
	response = alchemyapi.concepts("text", transcript)
	response = convert(response)

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
	response = convert(response)
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
	response = convert(response)
	keywords = []
	for kw in response["keywords"]:
		if float(kw["relevance"]) > 0.5:
			keywords.append(kw)

	for segment in transcript:
		if 'you' in segment:
			segment = segment["you"]
			#name
			element = listElementInString(["I'm ", "I am", "My name is ", "my name is ", 
				"people call me ", "call me ", "Call me "], segment)
			if element:
				people = entityOfTypeInSegment(['Person'], segment, entities)
				firstWord = segment.split(element)[1].split()[0]
				name = entityTextForWord(firstWord, people)
				if name:
					information["name"] = name

			#school
			element = listElementInString(["I go to ", "I study at ", "I attend ", "I went to ",
			 "I studied at ", "I attended ", "I graduated from ", "I go to the ", "I go to a ", 
			 "I study at the ", "I study at a ", "I attend a ", "I attend the ", "I graduated from the ",
			 "I graduated from a ", "I attended a ", "I attended the ", "I went to ", "I went to the ",
			 "I went to a ", "I studied at the ", "I studied at a "], segment)
			if element:
				schools = entityOfTypeInSegment(['Organization'], segment, entities)
				firstWord = segment.split(element)[1].split()[0]
				school = entityTextForWord(firstWord, schools)
				if school:
					information["school"] = school

			#employer
			element = listElementInString(["I work at ", "I work for ", "I work at a", "I work for a ",
				"I work at the ", "I work for the ", "I work in ", "I work in the ", "I work in a"], segment)
			if element:
				employers = entityOfTypeInSegment(['Company', 'Organization'], segment, entities)
				firstWord = segment.split(element)[1].split()[0]
				employer = entityTextForWord(firstWord, employers)
				if employer:
					information["employer"] = employer

				restOfSentence = segment.split(element)[1].replace("?", ".").replace("!", ".").split('.')[0]
				jobs = entityOfTypeInSegment(['JobTitle'], restOfSentence, entities)
				if jobs and "job" not in information:
					information["job"] = jobs[0]

			#jobtitle
			element = listElementInString(["I work as a", "I work as an ", "I work as, ", "I work as the " "I am a ",
			 "I am an ", "I am the ", "I am ", "I'm", "I'm a ", "I'm an "], segment)
			if element:
				jobs = entityOfTypeInSegment(['JobTitle'], segment, entities)
				firstWord = segment.split(element)[1].split()[0]
				job = entityTextForWord(firstWord, jobs)
				if job:
					information["job"] = job

				restOfSentence = segment.split(element)[1].replace("?", ".").replace("!", ".").split('.')[0]
				employers = entityOfTypeInSegment(['Company', 'Organization'], restOfSentence, entities)
				if employers and "employer" not in information:
					information["employer"] = employers[0]

			#hometown/homecountry
			element = listElementInString(["I went to school in ", "I spent my childhood in ",
				"I'm from ", "I am from ", "I lived in", "I live in ", "I grew up in "], segment)
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
							if float(keyword["sentiment"]["score"]) < 0.7:
								continue
							if "interests" in information and kwsgm not in information["interests"]:
								information["interests"].append(kwsgm)
							else:
								information["interests"] = [kwsgm]
						elif keyword["sentiment"]["type"] == "negative":
							if float(keyword["sentiment"]["score"]) > -0.7:
								continue
							if "dislikes" in information and kwsgm not in information["dislikes"]:
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

def convert(data):
    if isinstance(data, basestring):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(convert, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(convert, data))
    else:
        return data



