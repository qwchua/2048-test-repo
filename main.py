from gc import collect
import re
import subprocess

def getStarts(line):
    pattern = re.compile(r'@@\s-\d*,?\d*\s\+\d*,?\d* @@')
    match = pattern.findall(line)
    match = match[0]
    matches = match.split()

    start1 = matches[1][1:].split(',')[0]
    start2 = matches[2][1:].split(',')[0]

    return int(start1), int(start2)


def getResults(filename, numberOfCommits=200):
    gitlogcommand = 'git log -n {} --pretty="format:%H:%an:%ae:%cD" -- {} '.format(numberOfCommits,filename)
    unparsedlog = subprocess.run(gitlogcommand, shell=True, capture_output=True, text=True)
    unparsedlogstring = unparsedlog.stdout
    collection = unparsedlogstring.split('\n')
    commitgraph = []


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

    for i in range(len(commitgraph)-1):
    #for i in range(2):
        commithash0 = commitgraph[i]['hash']
        commithash1 = commitgraph[i+1]['hash']
        print("{} Doing hash0: {} and hash1: {}".format(i,commithash0,commithash1))
        gitdiffcommand = "git diff -U0 --numstat {} {} -- {}".format(commithash0,commithash1,filename)

        diff = subprocess.run(gitdiffcommand, shell=True, capture_output=True, text=True)
        unparsed_diff = diff.stdout
        #print(unparsed_diff)
        unparsed_diff = unparsed_diff.split("\n")
        #print(unparsed_diff[-1])
        start1 = 0
        start2 = 0

        queue1 = []
        queue2 = []

        negcurr = 0
        balance = 0

        for x in range(6, len(unparsed_diff)):
        #for x in range(6, len(unparsed_diff)):
            if len(unparsed_diff[x]) == 0 or unparsed_diff[x][0] == "@":
                while(queue1 or queue2):
                    if(queue1 and queue2 and queue1[0]["line"] == queue2[0]["line"]):
                        #do listen algo here
                        #current I set as who edited last
                        scoreboard[queue1[0]["line"]] = commitgraph[i+1]['author']
                        print("Edited line {}".format(queue1[0]["line"]))
                        queue1.pop(0)
                        queue2.pop(0)
                    elif(queue1):
                        lineToStartPoppingAt = queue1[0]["line"]
                        while(queue1):
                                scoreboard.pop(lineToStartPoppingAt)
                                print("Deleted line {}".format(lineToStartPoppingAt))
                                balance-=1
                                queue1.pop(0)
                                print("Scoreboard len: {}".format(len(scoreboard)))
                    elif(queue2):
                        scoreboard.insert(queue2[0]["line"], commitgraph[i+1]['author'])
                        print("Added on line {}".format(queue2[0]["line"]))
                        balance+=1
                        queue2.pop(0)
                    else:
                        print("Something went wrong while testing even")
                #print("Scoreboard len: {}".format(len(scoreboard)))

                if(len(unparsed_diff[x]) != 0):
                    start1, start2 = getStarts(unparsed_diff[x])
            elif unparsed_diff[x][0] == "-":
                queue1.append({"line":start1+balance, "content": unparsed_diff[1:]})
                start1+=1
            elif unparsed_diff[x][0] == "+":
                queue2.append({"line":start2, "content": unparsed_diff[1:]})
                start2+=1
            
        print("Round{} Scoreboard for hash0: {} and hash1: {}".format(i,commithash0,commithash1))
        for i in range(1,len(scoreboard)):
            print("{} : {}".format(i, scoreboard[i]))

    return scoreboard

    #for i in range(1,len(scoreboard)):
        #print("{} : {}".format(i, scoreboard[i]))

print(getResults("js/game_manager.js"))
