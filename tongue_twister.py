import pymysql.cursors
import pandas as pd
import time
import random
import string
import difflib

def handle_dialog(req, res):
	request	= req['request']
	command	= request['command']	
	res['response']['text']=command