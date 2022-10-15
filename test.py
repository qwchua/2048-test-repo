from gc import collect
import re
import subprocess
import numpy
import time
import concurrent.futures
from numba import njit
from numba.typed import List

def getgitdiff(commithash0,commithash1,filename):
    gitdiffcommand = "git diff -U0 --numstat {} {} -- {}".format(commithash0,commithash1,filename)

    diff = subprocess.run(gitdiffcommand, shell=True, capture_output=True, text=True)
    unparsed_diff = diff.stdout

    output = {
        "commit": commithash0 + ":" + commithash1,
        "data": unparsed_diff
    }

    return output

def getchanges(unparseddiff,hash0, hash1,oldauthor,newauthor):
    output = []
    diffs = unparseddiff.split("\n")

    start1 = 0
    start2 = 0

    queue1 = []
    queue2 = []
    balance = 0

    for x in range(6, len(diffs)):
        if len(diffs[x]) == 0 or diffs[x][0] == "@":
            while(queue1 or queue2):
                if(queue1 and queue2 and queue1[0]["line"] == queue2[0]["line"]):
                    #do Levenshtein Distance algo here
                    THRESHOLDPERCENT = 0.5
                    previousVersionLine = List(queue1[0]["content"])
                    newVersionLine = List(queue2[0]["content"])
                    distance = levenshteinDistanceDP(previousVersionLine,newVersionLine)
                    diffpercent = distance // len(previousVersionLine)

                    if diffpercent > THRESHOLDPERCENT:
                        #assign ownership to new version author
                        change = {
                            "line": queue1[0]['line'],
                            "type": "edit",
                            "owner": newauthor
                        }
                        output.append(change)
                    else:
                        #assign ownership to old version author as the diff % is not enough
                        change = {
                            "line": queue1[0]['line'],
                            "type": "edit",
                            "owner": oldauthor
                        }
                        output.append(change)
                    queue1.pop(0)
                    queue2.pop(0)
                elif(queue1):
                    lineToStartPoppingAt = queue1[0]["line"]
                    while(queue1):
                        change = {
                            "line": lineToStartPoppingAt,
                            "type": "delete",
                            "owner": "nil"
                        }
                        output.append(change)
                        balance-=1
                        queue1.pop(0)
                elif(queue2):
                    change = {
                            "line": queue2[0]["line"],
                            "type": "add",
                            "owner": newauthor
                        }
                    output.append(change)
                    balance+=1
                    queue2.pop(0)
                else:
                    print("Something went wrong while testing even")
            #print("Scoreboard len: {}".format(len(scoreboard)))

            if(len(diffs[x]) != 0):
                start1, start2 = getStarts(diffs[x])
        elif diffs[x][0] == "-":
            queue1.append({"line":start1+balance, "content": diffs[1:]})
            start1+=1
        elif diffs[x][0] == "+":
            queue2.append({"line":start2, "content": diffs[1:]})
            start2+=1

    return {
        "hash": hash0 + ":" + hash1,
        "data": output
    }
     

def getStarts(line):
    pattern = re.compile(r'@@\s-\d*,?\d*\s\+\d*,?\d* @@')
    match = pattern.findall(line)
    match = match[0]
    matches = match.split()

    start1 = matches[1][1:].split(',')[0]
    start2 = matches[2][1:].split(',')[0]

    return int(start1), int(start2)

@njit  
def levenshteinDistanceDP(token1,token2):
    distances = numpy.zeros((len(token1) + 1, len(token2) + 1))

    for t1 in range(len(token1) + 1):
        distances[t1][0] = t1

    for t2 in range(len(token2) + 1):
        distances[0][t2] = t2
        
    a = 0
    b = 0
    c = 0
    
    for t1 in range(1, len(token1) + 1):
        for t2 in range(1, len(token2) + 1):
            if (token1[t1-1] == token2[t2-1]):
                distances[t1][t2] = distances[t1 - 1][t2 - 1]
            else:
                a = distances[t1][t2 - 1]
                b = distances[t1 - 1][t2]
                c = distances[t1 - 1][t2 - 1]
                
                if (a <= b and a <= c):
                    distances[t1][t2] = a + 1
                elif (b <= a and b <= c):
                    distances[t1][t2] = b + 1
                else:
                    distances[t1][t2] = c + 1

    return distances[len(token1)][len(token2)]



# def getScoreboard(filename, numberofcommits=200):
#     gitlogcommand = 'git log -n {} --pretty="format:%H:%an:%ae:%cD" -- {} '.format(numberofcommits,filename)
#     unparsedlog = subprocess.run(gitlogcommand, shell=True, capture_output=True, text=True)
#     unparsedlogstring = unparsedlog.stdout
#     collection = unparsedlogstring.split('\n')
#     commitgraph = []
#     print("File was found in : {} commits".format(len(collection)))
#     print("Analyzing...")


#     for c in collection:
#         #remove the /n in end of the string
#         c = c[:-2]

#         list = c.split(":")

#         commit = {
#             "hash": list[0],
#             "author": list[1],
#             "email": list[2],
#             "date": list[3],
#         }
#         commitgraph.append(commit)

#     commitgraph.reverse()

#     gitshowcommand = "git show {}:{}".format(commitgraph[0]['hash'],filename)

#     show = subprocess.run(gitshowcommand, shell=True, capture_output=True, text=True)
#     unparsed_show = show.stdout
#     count = len(unparsed_show.split('\n'))

#     #remember to change index 0 to null; line0 = index 0
#     scoreboard = [commitgraph[0]["author"]] * (count + 1)

#     #print scoreboard
#     #for i in range(1,len(scoreboard)):
#         #print("{} : {}".format(i, scoreboard[i]))

#     for i in range(len(commitgraph)-1):
#         commithash0 = commitgraph[i]['hash']
#         commithash1 = commitgraph[i+1]['hash']
#         #print("{} Doing hash0: {} and hash1: {}".format(i,commithash0,commithash1))
#         gitdiffcommand = "git diff -U0 --numstat {} {} -- {}".format(commithash0,commithash1,filename)

#         diff = subprocess.run(gitdiffcommand, shell=True, capture_output=True, text=True)
#         unparsed_diff = diff.stdout

#         unparsed_diff = unparsed_diff.split("\n")

#         #print(unparsed_diff[0])
#         #countOfInsertAndDelete = unparsed_diff[0].split("     ")
#         #print("number of insertion: {} , number of deletion: {}".format(countOfInsertAndDelete[0], countOfInsertAndDelete[1]))

#         start1 = 0
#         start2 = 0

#         queue1 = []
#         queue2 = []
#         balance = 0
#         tt1 = time.perf_counter()

#         for x in range(6, len(unparsed_diff)):
#             if len(unparsed_diff[x]) == 0 or unparsed_diff[x][0] == "@":
#                 while(queue1 or queue2):
#                     if(queue1 and queue2 and queue1[0]["line"] == queue2[0]["line"]):
#                         #do Levenshtein Distance algo here
#                         THRESHOLDPERCENT = 0.5
#                         previousVersionLine = List(queue1[0]["content"])
#                         newVersionLine = List(queue2[0]["content"])
#                         #print("Calculating distance!")
#                         distance = levenshteinDistanceDP(previousVersionLine,newVersionLine)
#                         #print("Distance counted!")
#                         diffpercent = distance // len(previousVersionLine)

#                         if diffpercent > THRESHOLDPERCENT:
#                             #assign ownership to new version author
#                             scoreboard[queue1[0]["line"]] = commitgraph[i+1]['author']
#                         else:
#                             #assign ownership to old version author as the diff % is not enough
#                             scoreboard[queue1[0]["line"]] = commitgraph[i]['author']

#                         scoreboard[queue1[0]["line"]] = commitgraph[i+1]['author']
#                         #print("Edited line {}".format(queue1[0]["line"]))
#                         #scoreboard[queue1[0]["line"]] = commitgraph[i+1]['author']
#                         queue1.pop(0)
#                         queue2.pop(0)
#                     elif(queue1):
#                         lineToStartPoppingAt = queue1[0]["line"]
#                         while(queue1):
#                                 scoreboard.pop(lineToStartPoppingAt)
#                                 #print("Deleted line {}".format(lineToStartPoppingAt))
#                                 balance-=1
#                                 queue1.pop(0)
#                                 #print("Scoreboard len: {}".format(len(scoreboard)))
#                     elif(queue2):
#                         scoreboard.insert(queue2[0]["line"], commitgraph[i+1]['author'])
#                         #print("Added on line {}".format(queue2[0]["line"]))
#                         balance+=1
#                         queue2.pop(0)
#                     else:
#                         print("Something went wrong while testing even")
#                 #print("Scoreboard len: {}".format(len(scoreboard)))

#                 if(len(unparsed_diff[x]) != 0):
#                     start1, start2 = getStarts(unparsed_diff[x])
#             elif unparsed_diff[x][0] == "-":
#                 queue1.append({"line":start1+balance, "content": unparsed_diff[1:]})
#                 start1+=1
#             elif unparsed_diff[x][0] == "+":
#                 queue2.append({"line":start2, "content": unparsed_diff[1:]})
#                 start2+=1
            
#         tt2 = time.perf_counter()
#         #print(f'Commit finished in {tt2-tt1}')
        
            
#         #print("Round{} Scoreboard for hash0: {} and hash1: {}".format(i,commithash0,commithash1))
#         #for i in range(1,len(scoreboard)):
#             #print("{} : {}".format(i, scoreboard[i]))

#     return scoreboard

#     #for i in range(1,len(scoreboard)):
#         #click.echo("{} : {}".format(i, scoreboard[i]))

def test1(filename, numberofcommits=200):
    gitlogcommand = 'git log -n {} --pretty="format:%H:%an:%ae:%cD" -- {} '.format(numberofcommits,filename)
    unparsedlog = subprocess.run(gitlogcommand, shell=True, capture_output=True, text=True)
    unparsedlogstring = unparsedlog.stdout
    collection = unparsedlogstring.split('\n')
    commitgraph = []
    print("File was found in : {} commits".format(len(collection)))
    print("Analyzing...")

    for c in collection:
        #remove the /n in end of the string
        c = c[:-2]

        list = c.split(":")

        commit = {
            "hash": list[0],
            "author": list[1],
            "email": list[2],
            "date": list[3],
        }
        commitgraph.append(commit)

    commitgraph.reverse()

    gitshowcommand = "git show {}:{}".format(commitgraph[0]['hash'],filename)

    show = subprocess.run(gitshowcommand, shell=True, capture_output=True, text=True)
    unparsed_show = show.stdout
    count = len(unparsed_show.split('\n'))

    #remember to change index 0 to null; line0 = index 0
    scoreboard = [commitgraph[0]["author"]] * (count + 1)

    #print scoreboard
    #for i in range(1,len(scoreboard)):
        #print("{} : {}".format(i, scoreboard[i]))
    
    tt1 = time.perf_counter()

    for i in range(len(commitgraph)-1):
        commithash0 = commitgraph[i]['hash']
        commithash1 = commitgraph[i+1]['hash']
        #print("{} Doing hash0: {} and hash1: {}".format(i,commithash0,commithash1))
        gitdiffcommand = "git diff -U0 --numstat {} {} -- {}".format(commithash0,commithash1,filename)

        diff = subprocess.run(gitdiffcommand, shell=True, capture_output=True, text=True)
        unparsed_diff = diff.stdout

        unparsed_diff = unparsed_diff.split("\n")

        #print(unparsed_diff[0])
        #countOfInsertAndDelete = unparsed_diff[0].split("     ")
        #print("number of insertion: {} , number of deletion: {}".format(countOfInsertAndDelete[0], countOfInsertAndDelete[1]))
            
        #print("Round{} Scoreboard for hash0: {} and hash1: {}".format(i,commithash0,commithash1))
        #for i in range(1,len(scoreboard)):
            #print("{} : {}".format(i, scoreboard[i]))
    
    tt2 = time.perf_counter()
    print(f'git diff finished in {tt2-tt1}')

    return scoreboard

def test2(filename, numberofcommits=200):
    gitlogcommand = 'git log -n {} --pretty="format:%H:%an:%ae:%cD" -- {} '.format(numberofcommits,filename)
    unparsedlog = subprocess.run(gitlogcommand, shell=True, capture_output=True, text=True)
    unparsedlogstring = unparsedlog.stdout
    collection = unparsedlogstring.split('\n')
    commitgraph = []
    print("File was found in : {} commits".format(len(collection)))
    print("Analyzing...")

    for c in collection:
        #remove the /n in end of the string
        c = c[:-2]

        list = c.split(":")

        commit = {
            "hash": list[0],
            "author": list[1],
            "email": list[2],
            "date": list[3],
        }
        commitgraph.append(commit)

    commitgraph.reverse()

    gitshowcommand = "git show {}:{}".format(commitgraph[0]['hash'],filename)

    show = subprocess.run(gitshowcommand, shell=True, capture_output=True, text=True)
    unparsed_show = show.stdout
    count = len(unparsed_show.split('\n'))

    #remember to change index 0 to null; line0 = index 0
    scoreboard = [commitgraph[0]["author"]] * (count + 1)

    #print scoreboard
    #for i in range(1,len(scoreboard)):
        #print("{} : {}".format(i, scoreboard[i]))
    
    tt1 = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor() as executor:

        results = [executor.submit(getgitdiff,commitgraph[i]['hash'],commitgraph[i+1]['hash'],filename) for i in range(len(commitgraph)-1)]
        diffs = {}
        
        for f in concurrent.futures.as_completed(results):
            diffs[f.result()["commit"]] = f.result()["data"]

    print(len(diffs))
    
    tt2 = time.perf_counter()
    print(f'git diff finished in {tt2-tt1}')

    return scoreboard


def getScoreboard(filename, numberofcommits=200):
    t1 = time.perf_counter()
    gitlogcommand = 'git log -n {} --pretty="format:%H:%an:%ae:%cD" -- {} '.format(numberofcommits,filename)
    unparsedlog = subprocess.run(gitlogcommand, shell=True, capture_output=True, text=True)
    unparsedlogstring = unparsedlog.stdout
    collection = unparsedlogstring.split('\n')
    commitgraph = []
    print("File was found in : {} commits".format(len(collection)))
    print("Analyzing...")


    for c in collection:
        #remove the /n in end of the string
        c = c[:-2]

        list = c.split(":")

        commit = {
            "hash": list[0],
            "author": list[1],
            "email": list[2],
            "date": list[3],
        }
        commitgraph.append(commit)

    commitgraph.reverse()

    gitshowcommand = "git show {}:{}".format(commitgraph[0]['hash'],filename)

    show = subprocess.run(gitshowcommand, shell=True, capture_output=True, text=True)
    unparsed_show = show.stdout
    count = len(unparsed_show.split('\n'))

    #remember to change index 0 to null; line0 = index 0
    scoreboard = [commitgraph[0]["author"]] * (count + 1)

    diffs = {}

    with concurrent.futures.ThreadPoolExecutor() as executor:

        results = [executor.submit(getgitdiff,commitgraph[i]['hash'],commitgraph[i+1]['hash'],filename) for i in range(len(commitgraph)-1)]
        
        for f in concurrent.futures.as_completed(results):
            diffs[f.result()["commit"]] = f.result()["data"]

    for i in range(len(commitgraph)-1):
        commithash0 = commitgraph[i]['hash']
        commithash1 = commitgraph[i+1]['hash']
        diffhash = commithash0 + ":" + commithash1

        diff = diffs[diffhash]

        diff = diff.split("\n")

        start1 = 0
        start2 = 0

        queue1 = []
        queue2 = []
        balance = 0

        for x in range(6, len(diff)):
            if len(diff[x]) == 0 or diff[x][0] == "@":
                while(queue1 or queue2):
                    if(queue1 and queue2 and queue1[0]["line"] == queue2[0]["line"]):
                        #do Levenshtein Distance algo here
                        THRESHOLDPERCENT = 0.5
                        previousVersionLine = List(queue1[0]["content"])
                        newVersionLine = List(queue2[0]["content"])
                        #print("Calculating distance!")
                        distance = levenshteinDistanceDP(previousVersionLine,newVersionLine)
                        #print("Distance counted!")
                        diffpercent = distance // len(previousVersionLine)

                        if diffpercent > THRESHOLDPERCENT:
                            #assign ownership to new version author
                            scoreboard[queue1[0]["line"]] = commitgraph[i+1]['author']
                        else:
                            #assign ownership to old version author as the diff % is not enough
                            scoreboard[queue1[0]["line"]] = commitgraph[i]['author']

                        scoreboard[queue1[0]["line"]] = commitgraph[i+1]['author']
                        #print("Edited line {}".format(queue1[0]["line"]))
                        #scoreboard[queue1[0]["line"]] = commitgraph[i+1]['author']
                        queue1.pop(0)
                        queue2.pop(0)
                    elif(queue1):
                        lineToStartPoppingAt = queue1[0]["line"]
                        while(queue1):
                                scoreboard.pop(lineToStartPoppingAt)
                                #print("Deleted line {}".format(lineToStartPoppingAt))
                                balance-=1
                                queue1.pop(0)
                                #print("Scoreboard len: {}".format(len(scoreboard)))
                    elif(queue2):
                        scoreboard.insert(queue2[0]["line"], commitgraph[i+1]['author'])
                        #print("Added on line {}".format(queue2[0]["line"]))
                        balance+=1
                        queue2.pop(0)
                    else:
                        print("Something went wrong while testing even")
                #print("Scoreboard len: {}".format(len(scoreboard)))

                if(len(diff[x]) != 0):
                    start1, start2 = getStarts(diff[x])
            elif diff[x][0] == "-":
                queue1.append({"line":start1+balance, "content": diff[1:]})
                start1+=1
            elif diff[x][0] == "+":
                queue2.append({"line":start2, "content": diff[1:]})
                start2+=1
            
    t2 = time.perf_counter()
    print(f'Commit finished in {t2-t1}')
        
            
        #print("Round{} Scoreboard for hash0: {} and hash1: {}".format(i,commithash0,commithash1))
        #for i in range(1,len(scoreboard)):
            #print("{} : {}".format(i, scoreboard[i]))

    return scoreboard

    #for i in range(1,len(scoreboard)):
        #click.echo("{} : {}".format(i, scoreboard[i]))


def getScoreboard2(filename, numberofcommits=200):
    t1 = time.perf_counter()
    gitlogcommand = 'git log -n {} --pretty="format:%H:%an:%ae:%cD" -- {} '.format(numberofcommits,filename)
    unparsedlog = subprocess.run(gitlogcommand, shell=True, capture_output=True, text=True)
    unparsedlogstring = unparsedlog.stdout
    collection = unparsedlogstring.split('\n')
    commitgraph = []
    print("File was found in : {} commits".format(len(collection)))
    print("Analyzing...")


    for c in collection:
        #remove the /n in end of the string
        c = c[:-2]

        list = c.split(":")

        commit = {
            "hash": list[0],
            "author": list[1],
            "email": list[2],
            "date": list[3],
        }
        commitgraph.append(commit)

    commitgraph.reverse()

    gitshowcommand = "git show {}:{}".format(commitgraph[0]['hash'],filename)

    show = subprocess.run(gitshowcommand, shell=True, capture_output=True, text=True)
    unparsed_show = show.stdout
    count = len(unparsed_show.split('\n'))

    #remember to change index 0 to null; line0 = index 0
    scoreboard = [commitgraph[0]["author"]] * (count + 1)

    diffs = {}

    with concurrent.futures.ThreadPoolExecutor() as executor:

        results = [executor.submit(getgitdiff,commitgraph[i]['hash'],commitgraph[i+1]['hash'],filename) for i in range(len(commitgraph)-1)]
        
        for f in concurrent.futures.as_completed(results):
            diffs[f.result()["commit"]] = f.result()["data"]

    changes = {}
    
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = [executor.submit(getchanges, diffs[commitgraph[i]['hash']+":"+commitgraph[i+1]['hash']], commitgraph[i]['hash'], commitgraph[i+1]['hash'], commitgraph[i]['author'],commitgraph[i+1]['author']) for i in range(len(commitgraph)-1)]
        
        for f in concurrent.futures.as_completed(results):
            changes[f.result()["hash"]] = f.result()["data"]

    for i in range(len(commitgraph)-1):
        commithash0 = commitgraph[i]['hash']
        commithash1 = commitgraph[i+1]['hash']
        oldauthor = commitgraph[i]["author"]
        newauthor = commitgraph[i+1]["author"]
        diffhash = commithash0 + ":" + commithash1
        listofchanges = changes[diffhash]

        for c in listofchanges:
            if c["type"] == "add":
                scoreboard.insert(int(c["line"]), newauthor)
            elif c["type"] == "delete":
                scoreboard.pop(int(c["line"]))
            elif c["type"] == "edit":
                scoreboard[int(c["line"])] = c["owner"]


    t2 = time.perf_counter()
    print(f'Commit finished in {t2-t1}')

    return scoreboard


#test2("js/game_manager.js", 200)
if __name__ == '__main__':
    getScoreboard2("js/game_manager.js")
