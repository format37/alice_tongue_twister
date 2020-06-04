import pymysql.cursors
import pandas as pd
import time
import random
import string
import difflib
import requests
import urllib
import urllib.parse

sessionStorage = {}

def send_to_telegram(message):
	chat ='-440064142'
	headers = {
		"Origin": "http://scriptlab.net",
		"Referer": "http://scriptlab.net/telegram/bots/relaybot/",
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36'
		}
	url     = "http://scriptlab.net/telegram/bots/relaybot/relaylocked.php?chat="+chat+"&text="+urllib.parse.quote_plus(message)
	return requests.get(url,headers = headers)

def handle_dialog(req, res):

	try:
		send_to_telegram('check')
		user_id = req['session']['user_id']

		user_name = ''
		menu_id = 0
		user_text = req['request']['original_utterance']
		user_text_clear = remove_punctuation(user_text)

		if user_text == 'ping':
			res['response']['text'] = 'Спасибо, я в порядке!'
			return

		#MySQL++
		ServerName = 'localhost'
		Database = 'fastwords'
		username = 'root'
		password = ''
		con = pymysql.connect(ServerName, username, password, Database)
		with con:
			cur = con.cursor()
			query = "select name,menu_id from users where user='"+user_id+"';"
			mysql_df = pd.read_sql(query, con=con)
			if len(mysql_df)>0:			

				#user_name   = mysql_df.loc[0].values[0].decode('utf8')
				user_name   = mysql_df.loc[0].values[0]
				menu_id     = int(mysql_df.loc[0].values[1])

			if user_text_clear == 'выход':
				res['response']['text'] = 'Пока-пока!'
				res['response']['end_session'] = True
				add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
				return

			help_text = 'Данный навык разработан для тренировки дикции и памяти в игровой форме. Начните игру. Я произнесу скороговорку. В ответ вам следует её повторить слово в слово, как можно точнее. После оценки вашей скороговорки, мы её повторяем, или переходим к следующей. Для выхода из игры, произнесите слово "Выход".'

			if user_text_clear == 'помощь':
				res['response']['text'] = help_text
				add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
				return

			if user_text_clear == 'что ты умеешь':
				addiction=''
				query = 'select count(id) from words;'
				mysql_df = pd.read_sql(query, con=con)
				if len(mysql_df) > 0:
					words_count = str(int(mysql_df.loc[0].values[0]))
					addiction='Мне известно '+words_count+' скороговорок. '
				res['response']['text'] = addiction + 'Могу быть тренером для вашей дикции. Скороговорки можно произносить медленно, но непрерывно. Не читайте с экрана, если хотите размять память. Для меня понятны команды: Да, Нет, Помощь и Выход.'
				add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
				return

			if req['session']['new']:
				# Это новый пользователь.
				# Инициализируем сессию и поприветствуем его.
				if user_name.replace(' ', '')=='':
					res['response']['text'] = 'Здравствуйте! '+help_text+' Как Ваше имя?'
					# menu: 1 - Ожидаем, как представится пользователь
					query = "select count(id) from users where user='" + user_id + "';"
					mysql_df = pd.read_sql(query, con=con)
					if len(mysql_df) > 0:
						if int(mysql_df.loc[0].values[0])==0:
							query = "insert into users(user, name, menu_id) values('"+user_id+"','',1);"
							cur.execute(query)
					else:
						# Может таблица пользователей пуста..
						res['response']['text'] = 'Вы попали на секретный уровень 0. Никому об этом не говорите!'
					sessionStorage[user_id] = {
						'suggests': [
							random.choice(user_name_suggestions()),
							'Выход'
						]
					}
					res['response']['buttons'] = get_suggests(user_id)
					#add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
					return
				else:
					# Получим статистику по польователю
					stats=''
					query = "select ifnull(avg(score),0) from scores where user='"+user_id+"';"
					mysql_df = pd.read_sql(query, con=con)

					if len(mysql_df) > 0:
						score = str(int(mysql_df.loc[0].values[0]))
						stats=' Ваш средний балл: '+score+'.'
					# Получим лидера
					query = "drop table if exists lid cascade;"
					cur.execute(query)
					query = "create temporary table lid select user,ifnull(avg(score),0) as score from scores group by user having count(id)>2 limit 1;"
					cur.execute(query)
					query = "select users.user, users.name, lid.score from lid join users on lid.user=users.user;"
					mysql_df = pd.read_sql(query, con=con)
					if len(mysql_df) > 0:
						lid_id      = str(mysql_df.loc[0].values[0])
						#lid_name    = str(mysql_df.loc[0].values[1]).decode('utf8')
						lid_name    = str(mysql_df.loc[0].values[1])
						lid_score   = str(int(mysql_df.loc[0].values[2]))
						if lid_id==user_id:
							stats += ' Вы - лидер!'
						else:
							stats += ' Лидер - '+lid_name+', с показателем: '+lid_score+'.'
					res['response']['text'] = 'Здравствуйте '+user_name+'! '+help_text+stats+' Готовы к игре?'
					# menu: 3 - Играем или выход
					query = "update users set menu_id = 3 where user ='" + user_id + "';"
					cur.execute(query)
					sessionStorage[user_id] = {
						'suggests': [
							random.choice(menu_suggestions(3,True)[0]),  # Да
							random.choice(menu_suggestions(3,True)[1]),  # Выход
						]
					}
					res['response']['buttons'] = get_suggests(user_id)
					add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
					return

			if menu_id == 1:
				user_name=user_text
				res['response']['text'] = 'Хотите, что бы Вас называли "%s"?'%(user_name)
				# menu: 2 - Подтверждение имени
				query = "update users set menu_id = 2, name = '"+user_name+"' where user ='"+user_id+"';"
				cur.execute(query)
				sessionStorage[user_id] = {
					'suggests': [
						random.choice(menu_suggestions(2,True)[0]),  # Да
						random.choice(menu_suggestions(2,True)[1]),  # Нет
						'Выход'
					]
				}
				res['response']['buttons'] = get_suggests(user_id)
				#add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
				return

			if menu_id == 2:
				if user_text_clear in menu_suggestions(2,False)[0]: #Да
					res['response']['text'] = 'Приятно познакомиться, ' + user_name + '! Готовы к игре?'
					# menu: 3 - Играем или нет
					query = "update users set menu_id = 3 where user ='" + user_id + "';"
					cur.execute(query)
					sessionStorage[user_id] = {
						'suggests': [
							random.choice(menu_suggestions(3,True)[0]),  # Да
							random.choice(menu_suggestions(3,True)[1]),  # Выход
						]
					}
					res['response']['buttons'] = get_suggests(user_id)
					add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
					return
				else:
					res['response']['text'] = 'Как тогда мне Вас называть?'
					query = "update users set menu_id = 1 where user ='" + user_id + "';"
					cur.execute(query)
					sessionStorage[user_id] = {
						'suggests': [
							random.choice(user_name_suggestions())
						]
					}
					res['response']['buttons'] = get_suggests(user_id)
					add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
					return

			if menu_id == 3:
				if user_text_clear in menu_suggestions(3,False)[0]: #Да
					res['response']['text'] = generate_word(cur,con,user_id,'')
					add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
					return
				else:
					res['response']['text'] = 'Желаете продолжить игру?'
					# menu: 3 - Играем или выход
					query = "update users set menu_id = 3 where user ='" + user_id + "';"
					cur.execute(query)
					sessionStorage[user_id] = {
						'suggests': [
							random.choice(menu_suggestions(3, True)[0]),  # Да
							random.choice(menu_suggestions(3, True)[1]),  # Выход
						]
					}
					res['response']['buttons'] = get_suggests(user_id)
					add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
					return
				res['response']['text'] = 'Вы попали на секретный уровень 3. Никому об этом не говорите!'
				add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
				return

			if menu_id == 4:
				# Определим последнюю скороговорку пользователя
				mysql_df=get_last_user_word(con,cur,user_id)
				if len(mysql_df) > 0:
					#word = mysql_df.loc[0].values[0].decode('utf8')
					word = mysql_df.loc[0].values[0]
					word_id = str(mysql_df.loc[0].values[1])
					last_score = int(mysql_df.loc[0].values[2])
					# Оценим ответ пользователя
					word_clear=remove_punctuation(word)
					score=int(difflib.SequenceMatcher(None, word_clear, user_text_clear).ratio()*100)
					# Поместим оценку в БД
					query = "update scores set score="+str(score)+", event_date='"+time.strftime('%Y-%m-%d %H:%M:%S')+"' where user = '"+user_id+"' and word_id = "+word_id+";"
					cur.execute(query)
					# Сообщение пользователю
					addition=''
					if last_score<score and last_score>0:
						addition = ' На ' + str(score-last_score) + ' лучше, чем в прошлый раз!'
					elif last_score>score and last_score>0:
						addition = ' На ' + str(last_score-score) + ' меньше, чем в прошлый раз.'
					res['response']['text'] = 'Совпадение '+str(score)+' из ста.'+addition+' '+random.choice(menu_suggestions(5,True)[0])+', или '+random.choice(menu_suggestions(5,True)[1])+'?' # Повторим, или продолжим
					# menu: 5 - Повторим, или продолжим
					query = "update users set menu_id = 5 where user ='" + user_id + "';"
					cur.execute(query)
					sessionStorage[user_id] = {
						'suggests': [
							random.choice(menu_suggestions(5,True)[0]),  # Повторим
							random.choice(menu_suggestions(5,True)[1]),  # Продолжим
							'Выход'
						]
					}
					res['response']['buttons'] = get_suggests(user_id)
					add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
					return
				res['response']['text'] = 'Вы попали на секретный уровень 4Б. Никому об этом не говорите!'
				add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
				return

			if menu_id == 5:
				if user_text_clear in menu_suggestions(5,False)[1]: # продолжим
					res['response']['text'] = generate_word(cur,con,user_id,'')
					add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
					return
				else:
					# Определим последнюю скороговорку пользователя
					mysql_df = get_last_user_word(con, cur, user_id)
					if len(mysql_df) > 0:
						word_id = str(mysql_df.loc[0].values[1])
						res['response']['text'] = generate_word(cur,con,user_id,word_id)
						add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
						return
					res['response']['text'] = 'Вы попали на секретный уровень 5Б. Никому об этом не говорите!'
			res['response']['text'] = 'Вы попали на секретный уровень 5А. Никому об этом не говорите!'
			add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
			return
		#Возможно, нет соединения с Sql
		res['response']['text'] = 'Вы попали на секретный уровень 0. Никому об этом не говорите!'
		add_to_log(cur, user_id, menu_id, user_text, res['response']['text'])
	except Exception as e:
		log_error('handle_dialog',e)
		res['response']['text'] = 'Простите, меня отвлекли. Так о чём мы говорили?'

def get_last_user_word(con,cur,user_id):
	try:
		query = "drop table if exists last cascade;"
		cur.execute(query)
		query = "create temporary table last select word_id,event_date,score from scores where user = '" + user_id + "' order by event_date desc limit 1;"
		cur.execute(query)
		query = "select words.word, words.id, last.score from words inner join last on words.id=last.word_id;"
		mysql_df = pd.read_sql(query, con=con)
		return mysql_df
	except Exception as e:
		log_error('get_last_user_word',e)
		return ''
	
def generate_word(cur,con,user_id,in_word_id):
	try:
		# Выберем случайную скороговорку
		if in_word_id=='':
			mysql_df = get_last_user_word(con, cur, user_id)
			# Исключим последнюю скороговорку пользователя
			if len(mysql_df) > 0:
				word_id = str(mysql_df.loc[0].values[1])
				query = "select id,word from words where id<>"+word_id+" order by rand() limit 1;"
			else:
				query = "select id,word from words order by rand() limit 1;"
		else:
			# Выберем указанную скороговорку
			query = "select id,word from words where id="+in_word_id+";"

		mysql_df = pd.read_sql(query, con=con)
		if len(mysql_df) > 0:
			word_id = str(mysql_df.loc[0].values[0])
			#word = mysql_df.loc[0].values[1].decode('utf8')
			word = mysql_df.loc[0].values[1]

			# Проверим, имеются ли очки у пользователя по данной скороговорке
			query = "select score from scores where user='" + user_id + "' and word_id = " + word_id + ";"
			mysql_df = pd.read_sql(query, con=con)

			if len(mysql_df) > 0:  # Эту скороговорку пользователь уже решал
				# Запишем в скороговорку в очки пользователя как последнюю
				query = "update scores set event_date='" + time.strftime(
					'%Y-%m-%d %H:%M:%S') + "' where user = '" + user_id + "' and word_id = " + word_id + ";"
				cur.execute(query)
			else:  # Решает эту скороговорку впервые
				query = "insert into scores(user,word_id,score,event_date) values ('" + user_id + "'," + word_id + ",0,'" + time.strftime(
					'%Y-%m-%d %H:%M:%S') + "');"
				cur.execute(query)

			# menu: 4 - Ждем скороговорку, в исполнении пользователя
			query = "update users set menu_id = 4 where user ='" + user_id + "';"
			cur.execute(query)
			return word

		else:
			# Похоже, каталог скороговорок пуст..
			return 'Вы попали на секретный уровень 3. Никому об этом не говорите!'
	except Exception as e:
		log_error('generate_word',e)
		return 'Вы попали на секретный уровень 5Д. Никому об этом не говорите!'

def log_error(level,e):
	print(e.__doc__)
	#send_to_telegram(str(level)+': '+str(e.__doc__))
	
def user_name_suggestions():
	return [
		"Железный дровосек",
		"Сплюшка обыкновенная",
		"Капитан очевидность"
	]

def remove_punctuation(word):
	try:
		return word.translate({ord(c): None for c in ',.:-!?'}).lower()
	except Exception as e:
		log_error('remove_punctuation',e)
		return word
	
def menu_suggestions(menu_id,is_top):
	try:
		# Заполним структуру для всех пунктов меню
		menu = ['' for i in range(0, 6)]

		# menu: 2 - Да / Нет
		answers = []
		versions = [
			"Да",
			"Хорошо",
			"Ладно",
			"Давай",
			"Окей",
			"Ок"
		]
		answers.append(versions)
		versions = [
			"Нет",
			"Не хочу",
			"Подожди",
			"Отмена"
		]
		answers.append(versions)
		menu[2] = answers

		# menu: 3 - Готов / Выход
		answers = []
		versions = [
			"Да",
			"Хорошо",
			"Ладно",
			"Давай",
			"Окей",
			"Ок",
			"Играем",
			"Согласен",
			"Готов"
		]
		answers.append(versions)
		versions = [
			"Выход"
		]
		answers.append(versions)
		menu[3] = answers

		# menu: 5 - Повторим, или продолжим
		answers = []
		versions = [
			"Повторим",
			"Еще раз",
			"Повтор"
		]
		answers.append(versions)
		versions = [
			"Продолжим",
			"Дальше",
			"Следующая",
			"Следующий"
		]
		answers.append(versions)
		menu[5] = answers

		if not is_top:
			for menu_n in range(0,len(menu)):
				for answer_n in range(0,len(menu[menu_n])):
					for version_n in range(0,len(menu[menu_n][answer_n])):
						menu[menu_n][answer_n][version_n] = remove_punctuation(menu[menu_n][answer_n][version_n])

		return menu[menu_id]
	except Exception as e:
		log_error('menu_suggestions',e)
		return ["Выход"]
	
def add_to_log(cur,user,menu,text_in,text_out):
	try:
		query = "insert into log(user, menu, text_in, text_out, event_date) values('" + user + "', "+str(menu)+", '" + text_in + "', '" + text_out + "', '"+time.strftime('%Y-%m-%d %H:%M:%S')+"');"
		cur.execute(query)
	except Exception as e:
		log_error('add_to_log',e)
		res='sad story'
		
def get_suggests(user_id):
	session = sessionStorage[user_id]
	suggests = [
		{'title': suggest, 'hide': True}
		for suggest in session['suggests']
	]
	return suggests