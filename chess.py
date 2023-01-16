# %%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from chessdotcom import get_player_game_archives
import requests
import re
import nest_asyncio
nest_asyncio.apply()

# %%
class Game:
    def __init__(self, url, gameTime, moves, playedDate, playedTime, white, black):
        self.url = url #chess.com url
        self.gameTime = gameTime #1min (60), 3min (180), 5 min (300), etc
        self.moves = moves #total moves
        self.playedDate = playedDate #date of game (e.g. 2022.06.20)
        self.playedTime = playedTime #time of game (e.g. 15:24:10 UTC)
        self.white = white #dictionary of rating, username, and result of white side
        self.black = black #dictionary of rating, username, and result of black side
# %%
def get_user_games(username):
    """
    Only parameter is username of player
    Extracts the given user's games using the chess.com api and organizes facts about games using Game class.
    Sorted by month and kept in a dictionary
    """
    urls = get_player_game_archives(username).json['archives'] #returns list of urls for each month's games
    games_by_month = {}
    for i in urls:
        month = i[-7:] #last 7 characters of each endpoint are the month in YYYY/MM format
        games = requests.get(i).json()['games']
        game_list = [] #initialize list to keep track of games for every month
        for j in games:
            url = j['url'] #chess.com url
            gameTime = j['time_control'] #1min (60), 3min (180), 5 min (300), etc

            #calculate moves in the game
            moves = 0
            finished = False
            while finished == False:
                #checks for a complete turn (both players make a move)
                if re.search(f"{moves+1}\..+[%clk.0:..:...?.?].+{moves+1}\.\.\..+[%clk.0:..:...?.?]", j['pgn']):
                    moves += 1
                else:
                    #checks if game ended on an incomplete turn (only white made a move)
                    if re.search(f"{moves}\..+[%clk.0:..:...?.?].+{moves}\.\.\..+[%clk.0:..:...?.?].+{moves+1}\..+%clk .:..:...?.?]..\d-\d\\n$", j['pgn']):
                        moves += 1
                    finished = True
            
            #extract timezone, date, and time
            timezone_location = j['pgn'].find('Timezone')
            timezone = j['pgn'][timezone_location+10:timezone_location+13]
            playedDate_location = j['pgn'].find(f'{timezone}Date')
            playedDate = j['pgn'][playedDate_location+9:playedDate_location+19]
            playedTime_location = j['pgn'].find(f'{timezone}Time')
            playedTime = j['pgn'][playedTime_location+9:playedTime_location+17] + ' ' + timezone

            #rating, username, and result of white side
            white = {
                'rating' : j['white']['rating'],
                'username' : j['white']['username'],
                'result' : j['white']['result']
            }
            #rating, username, and result of black side
            black = {
                'rating' : j['black']['rating'],
                'username' : j['black']['username'],
                'result' : j['black']['result']
            }

            current_game = Game(url, gameTime, moves, playedDate, playedTime, white, black)
            game_list.append(current_game)
            
            
        games_by_month[month] = game_list
    return games_by_month

games = get_user_games('chriscorallo')

# %%
def get_match_result_by_colour(games):
    '''
    Games parameter is a dictionary of games by month created by get_user_games function
    returns 2 pie graphs of win percentage by colour
    '''
    #initialize dictionaries for result of each colour
    match_result_white = {'timeout':0, 'checkmated':0, 'repetition':0, 'timevsinsufficient':0, 'insufficient':0, 'stalemate':0, 'abandoned':0, 'resigned':0, 'win':0, 'agreed':0}
    match_result_black = {'timeout':0, 'checkmated':0, 'repetition':0, 'timevsinsufficient':0, 'insufficient':0, 'stalemate':0, 'abandoned':0, 'resigned':0, 'win':0, 'agreed':0}

    #iterate through games in each month key
    for month in games.keys(): 
        for game in games[month]:
            #check whether I was white or black, add result of match to according dictionary
            if game.white['username'] == 'chriscorallo':
                result = game.white['result']
                match_result_white[result] += 1
            else:
                result = game.black['result']
                match_result_black[result] += 1

    #sum all wins, draws, and losses for white
    white_wins = match_result_white['win']
    white_draws = sum(match_result_white[result] for result in match_result_white if result in ['repetition', 'timevsinsufficient', 'insufficient', 'stalemate', 'agreed']) 
    white_losses = sum(match_result_white[result] for result in match_result_white if result in ['timeout', 'checkmated', 'abandoned', 'resigned']) 

    #sum all wins, draws, and losses for black
    black_wins = match_result_black['win']
    black_draws = sum(match_result_black[result] for result in match_result_black if result in ['repetition', 'timevsinsufficient', 'insufficient', 'stalemate', 'agreed']) 
    black_losses = sum(match_result_black[result] for result in match_result_black if result in ['timeout', 'checkmated', 'abandoned', 'resigned'])

    #plotting time
    fig, (ax1,ax2) = plt.subplots(1,2,figsize = (10,10)) #2 plots
    fig.set_facecolor('lightgrey')
    labels = ['Win', 'Draw', 'Loss']
    colours = ['#d2b48c', '#3a3b3c', '#664229']

    white_data = np.array([white_wins, white_draws, white_losses])/(white_wins+white_draws+white_losses)
    ax1.pie(white_data, labels = labels, colors = colours, autopct='%.0f%%')
    ax1.set_title('Games as White')

    black_data = np.array([black_wins, black_draws, black_losses])/(black_wins+black_draws+black_losses)
    ax2.pie(black_data, labels = labels, colors = colours, autopct='%.2f%%')
    ax2.set_title('Games as Black')

    plt.show()

    return [white_wins, white_draws, white_losses], [black_wins, black_draws, black_losses]

get_match_result_by_colour(games)            

# %%
def get_nth_key(dictionary, n=0):
    if n < 0:
        n += len(dictionary)
    for i, key in enumerate(dictionary.keys()):
        if i == n:
            return key
    raise IndexError("dictionary index out of range")

def result_by_moves_per_game(games):
    '''
    games parameter is a dictionary of games by month created by get_user_games function
    returns bar graph of wins/losses by moves per game in groups of 10 (e.g. 10-19, 20-29, etc)
    '''
    #initialze dictionaries to keep track of wins/draws/losses for each grouping of moves
    wins = {'1-9': 0, '10-19': 0, '20-29': 0, '30-39': 0, '40-49': 0, '50-59': 0, '60-69': 0, '70-79': 0, '80+': 0} #key:moves, value:games
    draws = {'1-9': 0, '10-19': 0, '20-29': 0, '30-39': 0, '40-49': 0, '50-59': 0, '60-69': 0, '70-79': 0, '80+': 0} #key:moves, value:games
    losses =  {'1-9': 0, '10-19': 0, '20-29': 0, '30-39': 0, '40-49': 0, '50-59': 0, '60-69': 0, '70-79': 0, '80+': 0} #key:moves, value:games

    for month in games.keys(): 
        for game in games[month]:
            #only interested in 5 min games, can change or add any game times
            if game.gameTime != '300':
                continue

            if game.moves >= 80: #last grouping is 80+ so anything beyond has same index
                dic_index = 8
            else:
                dic_index = game.moves//10 #integer division to return index of dictionary key
            
            if game.white['username'] == 'chriscorallo': #check game object for what colour I was
                #depending on result add to the according dictionary
                if game.white['result'] == 'win':
                    da_key = get_nth_key(wins, dic_index)
                    wins[da_key] += 1
                elif game.white['result'] in ['timeout', 'checkmated', 'abandoned', 'resigned']:
                    da_key = get_nth_key(losses, dic_index)
                    losses[da_key] += 1
                else:
                    da_key = get_nth_key(draws, dic_index)
                    draws[da_key] += 1
            else:
                #depending on result add to the according dictionary
                if game.black['result'] == 'win':
                    da_key = get_nth_key(wins, dic_index)
                    wins[da_key] += 1
                elif game.black['result'] in ['timeout', 'checkmated', 'abandoned', 'resigned']:
                    da_key = get_nth_key(losses, dic_index)
                    losses[da_key] += 1
                else:
                    da_key = get_nth_key(draws, dic_index)
                    draws[da_key] += 1

    #plotting time!!!
    X = np.arange(9)
    fig = plt.figure()
    ax = fig.add_axes([0,0,1,1])
    ax.bar(X - 0.15, wins.values(), color = '#d2b48c', width = 0.3)
    #ax.bar(X, draws.values(), color = '#3d3d3d', width = 0.05)
    ax.bar(X + 0.15, losses.values(), color = '#664229', width = 0.3)

    ax.set_title('Wins/Losses by Moves Per Game')
    ax.set_ylabel('Games')
    ax.set_xticks(X, wins.keys())
    ax.legend(['Wins', 'Losses'])
    plt.show()

    return (wins,draws,losses)

result_by_moves_per_game(games)
# %%
def result_by_time_played(games):
    '''
    games parameter is a dictionary of games by month created by get_user_games function
    returns bar graph of wins/losses by moves per game in groups of 10 (e.g. 10-19, 20-29, etc)
    '''
    #initialze dictionaries to keep track of wins/draws/losses for each grouping of moves
    wins = {'00:00-02:59': 0, '03:00-05:59': 0, '06:00-08:59': 0, '09:00-11:59': 0, '12:00-14:59': 0, '15:00-17:59': 0, '18:00-20:59': 0, '21:00-23:59': 0} #key:moves, value:games
    draws = {'00:00-02:59': 0, '03:00-05:59': 0, '06:00-08:59': 0, '09:00-11:59': 0, '12:00-14:59': 0, '15:00-17:59': 0, '18:00-20:59': 0, '21:00-23:59': 0} #key:moves, value:games
    losses =  {'00:00-02:59': 0, '03:00-05:59': 0, '06:00-08:59': 0, '09:00-11:59': 0, '12:00-14:59': 0, '15:00-17:59': 0, '18:00-20:59': 0, '21:00-23:59': 0} #key:moves, value:games

    for month in games.keys(): 
        for game in games[month]:
            #only interested in 5 min games, can change or add any game times
            if game.gameTime != '300':
                continue
            
            #integer division to return index of key 
            if game.playedTime[0] == '0': #leading zeros are not permitted
                dic_index = (int(game.playedTime[1])-4)//3
            else:
                dic_index = (int(game.playedTime[0:2])-4)//3
            
            if game.white['username'] == 'chriscorallo': #check game object for what colour I was
                #depending on result add to the according dictionary
                if game.white['result'] == 'win':
                    da_key = get_nth_key(wins, dic_index)
                    wins[da_key] += 1
                elif game.white['result'] in ['timeout', 'checkmated', 'abandoned', 'resigned']:
                    da_key = get_nth_key(losses, dic_index)
                    losses[da_key] += 1
                else:
                    da_key = get_nth_key(draws, dic_index)
                    draws[da_key] += 1
            else:
                #depending on result add to the according dictionary
                if game.black['result'] == 'win':
                    da_key = get_nth_key(wins, dic_index)
                    wins[da_key] += 1
                elif game.black['result'] in ['timeout', 'checkmated', 'abandoned', 'resigned']:
                    da_key = get_nth_key(losses, dic_index)
                    losses[da_key] += 1
                else:
                    da_key = get_nth_key(draws, dic_index)
                    draws[da_key] += 1

    #plotting time!!!
    X = np.arange(8)
    fig = plt.figure()
    ax = fig.add_axes([0,0,1,1])
    ax.bar(X - 0.2, wins.values(), color = '#d2b48c', width = 0.4)
    #ax.bar(X, draws.values(), color = '#3d3d3d', width = 0.05)
    ax.bar(X + 0.2, losses.values(), color = '#664229', width = 0.4)

    ax.set_title('Wins/Losses at Times of day')
    ax.set_ylabel('Games')
    ax.set_xticks(X, wins.keys())
    ax.legend(['Wins', 'Losses'], loc = 'upper left')
    plt.setp(ax.get_xticklabels(), rotation=45, horizontalalignment='right')
    plt.show()

    return (wins,draws,losses)

result_by_time_played(games)

#most common openings
#['url', 'pgn', 'time_control', 'end_time', 'rated', 'tcn', 'uuid', 'initial_setup', 'fen', 'time_class', 'rules', 'white', 'black']
#draw:repition, timevsinsufficient, insufficient, stalemate, agreed
#win: win
#loss: timeout, checkmated, abandoned, resigned

